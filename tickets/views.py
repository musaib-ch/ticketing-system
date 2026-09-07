from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from .models import Ticket, TicketMessage, Attachment, TicketLog
from .forms import TicketForm, TicketMessageForm
from .utils import filter_and_sort_tickets, paginate_tickets, sanitize_csv_field
from users.decorators import staff_role_required

@login_required
def dashboard(request):
    user = request.user
    
    if user.role in ['admin', 'functional_rep']:
        active_role = request.session.get('active_role')
        if not active_role:
            return redirect('role_selection')
            
        if active_role == 'employee':
            return redirect('queue')
    else:
        return redirect('queue')
        
    # 1. Base Queryset
    if user.role == 'functional_rep':
        tickets = Ticket.objects.filter(team__in=user.teams.all())
    else:
        tickets = Ticket.objects.all()
        
    # 2. Search & Sort
    tickets = filter_and_sort_tickets(tickets, request)
        
    # 3. Context & Counts
    context = {}
    context['tickets'] = tickets.select_related('requester', 'team')[:15]
    
    # Calculate global or scoped base for charts
    if user.role == 'employee':
        chart_qs = Ticket.objects.filter(requester=user)
    elif user.role == 'functional_rep':
        chart_qs = Ticket.objects.filter(team__in=user.teams.all())
    else:
        chart_qs = Ticket.objects.all()
        
    context['open_count'] = chart_qs.filter(status__in=['open', 'in_progress']).count()
    context['resolved_count'] = chart_qs.filter(status='resolved').count()
    if user.role == 'admin':
        context['unassigned_count'] = chart_qs.filter(team__isnull=True).count()
        
    import json
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Avg

    now = timezone.now()
    
    # Aging Tickets
    a_24 = chart_qs.filter(status__in=['open', 'in_progress'], created_at__gte=now - timedelta(days=1)).count()
    a_1_3 = chart_qs.filter(status__in=['open', 'in_progress'], created_at__gte=now - timedelta(days=3), created_at__lt=now - timedelta(days=1)).count()
    a_3p = chart_qs.filter(status__in=['open', 'in_progress'], created_at__lt=now - timedelta(days=3)).count()
    context['aging_data'] = json.dumps([a_24, a_1_3, a_3p])

    # Status Data
    status_counts = list(chart_qs.values('status').annotate(c=Count('id')))
    context['status_data'] = json.dumps(status_counts)

    # Department Data
    dept_counts = list(chart_qs.values('team__name').annotate(c=Count('id')))
    context['dept_data'] = json.dumps(dept_counts)
    
    # Heatmap Data (Priority vs Team)
    heatmap_qs = list(chart_qs.exclude(team__isnull=True).values('team__name', 'priority').annotate(c=Count('id')))
    context['heatmap_data'] = json.dumps(heatmap_qs)
    
    # Agent Workload
    agent_qs = list(chart_qs.exclude(assigned_agent__isnull=True).values('assigned_agent__first_name', 'assigned_agent__last_name').annotate(c=Count('id'), avg_time=Avg('time_spent_minutes')))
    context['agent_workload'] = json.dumps(agent_qs)

    # Busy Days (Last 30 Days Heatmap/Bar)
    from django.db.models.functions import TruncDate
    thirty_days_ago = now - timedelta(days=30)
    busy_days_qs = list(
        chart_qs.filter(created_at__gte=thirty_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date', 'team__name')
        .annotate(c=Count('id'))
        .order_by('date')
    )
    for item in busy_days_qs:
        if item['date']:
            item['date'] = item['date'].strftime('%Y-%m-%d')
    context['busy_days_data'] = json.dumps(busy_days_qs)

    # Average Resolution Time (in minutes) by Team
    avg_res_qs = list(
        chart_qs.filter(status='resolved')
        .exclude(team__isnull=True)
        .values('team__name')
        .annotate(avg_time=Avg('time_spent_minutes'))
    )
    context['avg_resolution_data'] = json.dumps(avg_res_qs)

    return render(request, 'dashboard.html', context)

@login_required
def update_dashboard_prefs(request):
    import json
    if request.method != 'POST':
        return JsonResponse({"status": "invalid_method"}, status=405)
    try:
        prefs = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Invalid JSON payload."}, status=400)
    request.user.dashboard_prefs = json.dumps(prefs)
    request.user.save(update_fields=['dashboard_prefs'])
    return JsonResponse({"status": "ok"})

@login_required
def queue(request):
    user = request.user
    if user.role == 'employee' or request.session.get('active_role') == 'employee':
        tickets = Ticket.objects.filter(requester=request.user)
        page_title = 'My Queries'
    elif user.role == 'admin':
        tickets = Ticket.objects.all()
        page_title = 'All Queries'
    else:
        # Reps should not be here, they have department_queue, but just in case
        return redirect('department_queue')
        
    tickets = filter_and_sort_tickets(tickets, request).select_related('requester', 'team')
    page_obj = paginate_tickets(tickets, request)
    return render(request, 'queue.html', {'tickets': page_obj, 'page_obj': page_obj, 'page_title': page_title})

@login_required
def department_queue(request):
    if request.user.role == 'employee' or request.session.get('active_role') == 'employee':
        return redirect('dashboard')
        
    tickets = Ticket.objects.filter(team__in=request.user.teams.all())
    tickets = filter_and_sort_tickets(tickets, request).select_related('requester', 'team')
    page_obj = paginate_tickets(tickets, request)
    return render(request, 'queue.html', {'tickets': page_obj, 'page_obj': page_obj, 'page_title': 'Department Queries'})

@login_required
def submit_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.requester = request.user
            
            # Phase 7: Auto-Assignment (Round Robin) based on department
            if ticket.team:
                from django.db.models import Count, Q
                reps = ticket.team.members.filter(role='functional_rep')
                if reps.exists():
                    reps = reps.annotate(
                        open_tickets_count=Count('assigned_tickets', filter=Q(assigned_tickets__status__in=['open', 'in_progress']))
                    ).order_by('open_tickets_count')
                    ticket.assigned_agent = reps.first()
            
            ticket.save()
            
            attachment = form.cleaned_data.get('attachment')
            if attachment:
                Attachment.objects.create(ticket=ticket, file=attachment)
            
            from .utils import send_ticket_notification
            send_ticket_notification(ticket, is_new=True)
            
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
        
    import json
    from users.models import Team
    team_data = {}
    for team in Team.objects.all():
        if team.query_categories:
            team_data[str(team.id)] = [c.strip() for c in team.query_categories.split(',')]
            
    return render(request, 'submit.html', {'form': form, 'team_categories_json': json.dumps(team_data)})

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related('requester', 'team', 'assigned_agent'), pk=pk)
    acting_as_employee = (
        request.user.role == 'employee' or
        request.session.get('active_role') == 'employee'
    )
    
    # Simple permission check
    if acting_as_employee and ticket.requester != request.user:
        return redirect('dashboard')
    if not acting_as_employee and request.user.role == 'functional_rep' and ticket.team not in request.user.teams.all():
        return redirect('dashboard')
        
    if ticket.has_unread_messages:
        ticket.has_unread_messages = False
        ticket.save(update_fields=['has_unread_messages'])
        
    if request.method == 'POST':
        # Reopening is permitted only while the configured post-close window is open.
        if 'reopen_ticket' in request.POST:
            from datetime import timedelta
            from django.utils import timezone
            from users.models import Branding

            window_days = max(0, Branding.get_settings().ticket_reopen_window_days)
            can_reopen = bool(
                ticket.status == 'closed' and ticket.closed_at and
                timezone.now() < ticket.closed_at + timedelta(days=window_days)
            )
            if not can_reopen:
                messages.error(request, 'This ticket can no longer be reopened.')
            else:
                ticket.status = 'in_progress'
                ticket.closed_at = None
                ticket.save(update_fields=['status', 'closed_at', 'updated_at'])
                TicketLog.objects.create(
                    ticket=ticket, actor=request.user, action='Reopened',
                    details='Ticket reopened within the configured reopening window.'
                )
                messages.success(request, 'Ticket reopened and returned to In Progress.')
            return redirect('ticket_detail', pk=ticket.pk)

        # Admin Routing
        if 'assign_team' in request.POST and request.user.role == 'admin' and not acting_as_employee:
            team_id = request.POST.get('team_id')
            agent_id = request.POST.get('assigned_agent_id')
            if team_id:
                from users.models import Team, User
                team = get_object_or_404(Team, pk=team_id)
                assigned_agent = None
                if agent_id:
                    assigned_agent = get_object_or_404(
                        User.objects.filter(role='functional_rep', teams=team), pk=agent_id
                    )

                previous_team = ticket.team
                previous_agent = ticket.assigned_agent
                ticket.team = team
                ticket.assigned_agent = assigned_agent
                ticket.save(update_fields=['team', 'assigned_agent', 'updated_at'])

                changes = []
                if previous_team != team:
                    changes.append(f"Department changed from {previous_team.name if previous_team else 'Unassigned'} to {team.name}")
                if previous_agent != assigned_agent:
                    changes.append(f"Representative changed from {previous_agent.get_full_name() or previous_agent.username if previous_agent else 'Unassigned'} to {assigned_agent.get_full_name() or assigned_agent.username if assigned_agent else 'Unassigned'}")
                if changes:
                    TicketLog.objects.create(ticket=ticket, actor=request.user, action='Assigned', details='; '.join(changes))

                from .utils import send_ticket_notification
                send_ticket_notification(ticket, is_new=True)
            return redirect('ticket_detail', pk=ticket.pk)
            
        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            new_status = request.POST.get('status')
            is_agent = not acting_as_employee and request.user.role in ['admin', 'functional_rep']
            if new_status and (not is_agent or new_status not in dict(Ticket.STATUS_CHOICES)):
                new_status = None
            if new_status == 'closed' and not form.cleaned_data['body'].strip():
                form.add_error('body', 'Closing remarks are required before a ticket can be closed.')
            if form.errors:
                # Fall through to re-render the form with its validation feedback.
                pass
            else:
                previous_status = ticket.status
                msg = form.save(commit=False)
                msg.ticket = ticket
                msg.sender = request.user
                # Security check: Only Admins or Reps (assigned to this team) can create internal notes
                if msg.is_internal:
                    if acting_as_employee:
                        msg.is_internal = False
                    elif request.user.role == 'functional_rep' and ticket.team not in request.user.teams.all():
                        msg.is_internal = False

                msg.save()
                ticket.has_unread_messages = True

                if new_status and new_status != previous_status:
                    ticket.status = new_status
                    from django.utils import timezone
                    if new_status == 'closed':
                        ticket.closed_at = timezone.now()
                    elif previous_status == 'closed':
                        ticket.closed_at = None
                    TicketLog.objects.create(
                        ticket=ticket, actor=request.user, action='Status Changed',
                        details=f"Status changed from {dict(Ticket.STATUS_CHOICES)[previous_status]} to {dict(Ticket.STATUS_CHOICES)[new_status]}."
                    )

                # Log time spent if provided
                time_spent = request.POST.get('time_spent_minutes')
                if is_agent and time_spent and time_spent.isdigit():
                    ticket.time_spent_minutes += int(time_spent)
                ticket.save()

                attachment = form.cleaned_data.get('attachment')
                if attachment:
                    Attachment.objects.create(ticket=ticket, message=msg, file=attachment)

                from .utils import send_reply_to_requester
                if is_agent:
                    send_reply_to_requester(msg)

                return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketMessageForm()
        
    canned_responses = []
    if ticket.team and ticket.team.canned_responses:
        import json
        try:
            canned_responses = json.loads(ticket.team.canned_responses)
        except (TypeError, ValueError):
            pass
            
    from datetime import timedelta
    from django.utils import timezone
    from users.models import Team, Branding, User
    reopen_window = max(0, Branding.get_settings().ticket_reopen_window_days)
    can_reopen = bool(ticket.status == 'closed' and ticket.closed_at and timezone.now() < ticket.closed_at + timedelta(days=reopen_window))
    reps = User.objects.filter(role='functional_rep').prefetch_related('teams').order_by('first_name', 'last_name', 'username')
    return render(request, 'ticket_detail.html', {
        'ticket': ticket, 'form': form, 'teams': Team.objects.all(), 'reps': reps,
        'canned_responses': canned_responses, 'can_reopen': can_reopen,
        'is_agent_mode': not acting_as_employee and request.user.role in ['admin', 'functional_rep'],
    })

@login_required
def export_tickets_csv(request):
    import csv
    from django.http import HttpResponse
    
    if request.user.role == 'employee' or request.session.get('active_role') == 'employee':
        return redirect('dashboard')
        
    if request.user.role == 'admin':
        tickets = Ticket.objects.all().order_by('-created_at')
    else:
        tickets = Ticket.objects.filter(team__in=request.user.teams.all()).order_by('-created_at')
        
    tickets = tickets.select_related('requester', 'team', 'assigned_agent')
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        tickets = tickets.filter(
            Q(ticket_number__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(requester__first_name__icontains=q) |
            Q(requester__last_name__icontains=q)
        )
        
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="tickets_export.csv"'},
    )

    writer = csv.writer(response)
    writer.writerow(['Ticket Number', 'Subject', 'Category', 'Department', 'Assigned Agent', 'Requester', 'Status', 'Priority', 'Creation Date', 'Completion Date', 'TAT (Hours)'])
    
    for t in tickets:
        tat = ""
        end_time = t.resolved_at or t.closed_at
        if end_time:
            delta = end_time - t.created_at
            tat = round(delta.total_seconds() / 3600.0, 2)
            
        # Fields below can contain arbitrary employee-supplied text (title,
        # category); sanitize before writing so a title like "=cmd|..." can't
        # execute as a formula when the export is opened in Excel/Sheets.
        writer.writerow([
            sanitize_csv_field(t.ticket_number),
            sanitize_csv_field(t.title),
            sanitize_csv_field(t.query_relevance),
            sanitize_csv_field(t.team.name if t.team else "Unassigned"),
            sanitize_csv_field(t.assigned_agent.get_full_name() or t.assigned_agent.username if t.assigned_agent else "Unassigned"),
            sanitize_csv_field(t.requester.get_full_name() or t.requester.username),
            t.get_status_display(),
            t.get_priority_display(),
            t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else "",
            tat
        ])

    return response

def knowledge_base(request):
    from .models import KnowledgeArticle
    from users.models import Team
    from django.db.models import Q
    from collections import defaultdict

    sort_by = request.GET.get('sort', 'views')
    category = request.GET.get('category', 'all')
    view_mode = request.GET.get('view', 'all')
    search_q = request.GET.get('q', '').strip()

    queryset = KnowledgeArticle.objects.filter(is_published=True).select_related('team')

    if search_q:
        queryset = queryset.filter(Q(title__icontains=search_q) | Q(content__icontains=search_q))

    if category != 'all':
        if category == 'general':
            queryset = queryset.filter(team__isnull=True)
        else:
            queryset = queryset.filter(team__id=category)

    if sort_by == 'newest':
        queryset = queryset.order_by('-created_at')
    elif sort_by == 'title':
        queryset = queryset.order_by('title')
    else: # views
        queryset = queryset.order_by('-view_count')

    articles = list(queryset)

    # Group by category / department
    grouped_map = defaultdict(list)
    for art in articles:
        team_name = art.team.name if art.team else "General HR & Policies"
        grouped_map[team_name].append(art)

    grouped_articles = [{'team_name': k, 'articles': v} for k, v in grouped_map.items()]
    teams = Team.objects.all()

    context = {
        'articles': articles,
        'grouped_articles': grouped_articles,
        'teams': teams,
        'selected_sort': sort_by,
        'selected_category': category,
        'selected_view': view_mode,
        'search_q': search_q,
    }
    return render(request, 'knowledge_base.html', context)

def article_detail(request, pk):
    from .models import KnowledgeArticle
    article = get_object_or_404(KnowledgeArticle, pk=pk, is_published=True)
    KnowledgeArticle.objects.filter(pk=pk).update(view_count=article.view_count + 1)
    return render(request, 'article_detail.html', {'article': article})

def _kb_manageable_articles(user):
    """Articles a given staff user is allowed to see/manage in the KB admin screens.

    Admins manage everything. Reps only manage articles for their own
    department(s) - department-less "General" articles are admin-only, since
    they're visible org-wide.
    """
    from .models import KnowledgeArticle
    if user.role == 'admin':
        return KnowledgeArticle.objects.all()
    return KnowledgeArticle.objects.filter(team__in=user.teams.all())

@staff_role_required
def manage_kb(request):
    articles = _kb_manageable_articles(request.user).order_by('-created_at')
    return render(request, 'manage_kb.html', {'articles': articles})

@staff_role_required
def edit_article(request, pk=None):
    from .models import KnowledgeArticle
    from .forms import KnowledgeArticleForm
    if pk:
        article = get_object_or_404(_kb_manageable_articles(request.user), pk=pk)
    else:
        article = None
        
    if request.method == 'POST':
        form = KnowledgeArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            art = form.save(commit=False)
            # Reps may only publish to their own department(s); admins may
            # also publish org-wide "General" articles (team left blank).
            if request.user.role != 'admin' and art.team not in request.user.teams.all():
                form.add_error('team', 'You can only publish articles for your own department.')
            else:
                if not pk:
                    art.author = request.user
                if request.POST.get('remove_attachment') == '1':
                    art.file = None
                art.save()
                messages.success(request, "Article saved successfully!")
                return redirect('manage_kb')
    else:
        form = KnowledgeArticleForm(instance=article)
        if request.user.role != 'admin':
            form.fields['team'].queryset = request.user.teams.all()
            form.fields['team'].empty_label = None
    return render(request, 'edit_article.html', {'form': form, 'article': article})

@staff_role_required
def delete_article(request, pk):
    if request.method == 'POST':
        article = get_object_or_404(_kb_manageable_articles(request.user), pk=pk)
        article.delete()
        messages.success(request, "Article deleted.")
    return redirect('manage_kb')
