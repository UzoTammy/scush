from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import View, TemplateView, ListView
from staff.models import Employee
from .models import Question
import random
from django.contrib import messages


class SurveyHomeView(TemplateView):
    template_name = 'survey/home.html'


class SurveyCreateView(View):
    
    def get(self, request, *args, **kwargs):
        for staff in Employee.objects.all():
            pin = random.randint(1000, 9999)
            code = int((str(pin)) + str(staff.id).zfill(3))
            try:
                obj = Question(code=code, staff=staff)
                obj.save()
            except:
                return HttpResponse(f'''<h3>This request already exist, contact Admin for reset if you will need to 
                recreate survey</h3>''')

        return HttpResponse(f'{Employee.objects.all().count()} staff codes Created')


class SurveyCodeView(View):
    template_name = 'survey/entry_form.html'
   
    def get(self, request, **kwargs):
        context = {
            'heading': 'Number of Children',
        }
        if request.GET != {}:
            if request.GET['pin'] != '':
                return redirect('survey-update', pin=request.GET['pin'])
            else:
                messages.info(request, "You must enter your 7-digit code to participate")
            
        return render(request, 'survey/entry_form.html', context)
        

class SurveyUpdateView(View):

    def get(self, request, **kwargs):
        obj = get_object_or_404(Question, code=kwargs['pin'])
        
        return render(request, 'survey/update_form.html', {'staff': obj})
    
    def post(self, request, **kwargs):
        obj = get_object_or_404(Question, code=self.kwargs['pin'])
        if request.POST['number_of_kids'] != '':
            obj.number_kids = int(request.POST['number_of_kids'])
            obj.date = timezone.now()
            obj.save()
            messages.info(request, 'You have successfully updated your record. Thanks for participating!!!')
            return redirect('index')
        messages.info(request, "Enter your number of children or 0 if you dont't have yet")
        return render(request, 'survey/update_form.html', {'staff': obj})


class SurveyListView(ListView):
    model = Question

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total'] = self.get_queryset().aggregate(Sum('number_kids'))['number_kids__sum']
        return context