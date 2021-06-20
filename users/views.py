from django.shortcuts import render, redirect
from .forms import UserRegisterForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserUpdateForm, ProfileUpdateForm


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
