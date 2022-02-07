from django.shortcuts import render, redirect
from .forms import UserRegisterForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserUpdateForm, ProfileUpdateForm
import json
from django.views.generic import ListView
from django.contrib.auth.models import User


def allow_admin(user):
    if user.groups.filter(name='Administrator').exists():
        return True
    return False


@login_required()
@user_passes_test(allow_admin)
def register(request, **kwargs):
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
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)
        if request.FILES:
            if p_form.is_valid():
                p_form.save()
                messages.success(request, f'Profile picture updated successfully!!')
                return redirect('profile')
        else:
            if u_form.is_valid():
                u_form.save()
                messages.success(request, f'Profile info updated successfully!!')
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
    with open('extrafiles/choices.json') as rf:
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

        with open('extrafiles/choices.json', 'w') as wf:
            json.dump(content, wf, indent=2)
    else:
        messages.info(request, 'no choice value to add')
    return redirect('home')


class UsersListView(ListView):
    model = User
    
    def get_queryset(self):
        # to list all users working at Ozone
        return super().get_queryset().filter(username__contains='-').order_by('-pk')
    
    

        