import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView
from django.contrib.auth.models import User
from django.conf import settings
from .forms import UserRegisterForm, UserInviteForm
from .forms import UserUpdateForm, ProfileUpdateForm
from .models import UserInvite
from django.contrib.auth.mixins import LoginRequiredMixin

def allow_admin(user):
    if user.is_superuser:
        return True
    if user.groups.filter(name='Administrator').exists():
        return True
    return False


@login_required()
def register(request, **kwargs):
    if not allow_admin(request.user):
        raise PermissionDenied
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Your registration as {username} is successful!!')
            return redirect('home')
    else:
        form = UserRegisterForm()
    context = {
        'title': 'register',
        'form': form,
    }
    return render(request, 'users/register.html', context)


@login_required
def invite_create(request):
    if not allow_admin(request.user):
        raise PermissionDenied
    if request.method == 'POST':
        form = UserInviteForm(request.POST)
        if form.is_valid():
            invite = UserInvite.objects.create(
                email=form.cleaned_data['email'],
                created_by=request.user,
            )
            messages.success(request, f'Invite link created for {invite.email}.')
            return redirect('user-invite-create')
    else:
        form = UserInviteForm()
    invites = [
        (invite, request.build_absolute_uri(reverse('register-invite', kwargs={'token': invite.token})))
        for invite in UserInvite.objects.select_related('created_by', 'used_by')
    ]
    context = {
        'title': 'invite user',
        'form': form,
        'invites': invites,
    }
    return render(request, 'users/invite_create.html', context)


@login_required
def invite_delete(request, pk):
    if not allow_admin(request.user):
        raise PermissionDenied
    invite = get_object_or_404(UserInvite, pk=pk)
    if request.method == 'POST':
        email = invite.email
        invite.delete()
        messages.success(request, f'Invite for {email} has been deleted.')
    return redirect('user-invite-create')


def register_via_invite(request, token):
    invite = get_object_or_404(UserInvite, token=token)
    if not invite.is_valid():
        return render(request, 'users/invite_expired.html')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            invite.used = True
            invite.used_by = user
            invite.save(update_fields=['used', 'used_by'])
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Welcome, {user.username}! Your account is ready.')
            return redirect('home')
    else:
        form = UserRegisterForm(initial={'email': invite.email})
    context = {
        'title': 'set up your account',
        'form': form,
        'invite': invite,
    }
    return render(request, 'users/register_invite.html', context)


@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)
        if request.FILES:
            if p_form.is_valid():
                p_form.save()
                messages.success(request, 'Profile picture updated successfully!!')
                return redirect('profile')
        else:
            if u_form.is_valid():
                u_form.save()
                messages.success(request, 'Profile info updated successfully!!')
                return redirect('profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    context = {
        'u_form': u_form,
        'p_form': p_form,
    }
    return render(request, 'users/profile.html', context)


@login_required
def add_choice(request):
    base_root = settings.BASE_DIR
    with open(base_root / 'json' / 'choices.json') as rf:
        content = json.load(rf)

    if request.GET['choiceValue'] != '':
        if request.GET['choiceType'] == 'bank':
            banks = content['banks']
            banks.append(request.GET['choiceValue'])
            content['banks'] = banks
        elif request.GET['choiceType'] == 'branch':
            branches = content['branches']
            branches.append(request.GET['choiceValue'])
            content['branches'] = branches
        elif request.GET['choiceType'] == 'department':
            departments = content['departments']
            departments.append(request.GET['choiceValue'])
            content['departments'] = departments
        else:
            positions = content['positions']
            positions.append(request.GET['choiceValue'])
            content['positions'] = positions

        with open(base_root / 'json' / 'choices.json', 'w') as wf:
            json.dump(content, wf, indent=2)
    else:
        messages.info(request, 'no choice value to add')
    return redirect('home')


class UsersListView(LoginRequiredMixin, ListView):
    model = User
    
    def get_queryset(self):
        # to list all users working at Ozone
        return super().get_queryset().filter(username__contains='-').order_by('-pk')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_without_dash'] = User.objects.exclude(username__contains='-')
        return context
    

class UserGroupView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'auth/group_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = list((user, user.groups.all()) for user in super().get_queryset() if user.groups.exists())
        return context