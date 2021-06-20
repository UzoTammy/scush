import os
from django.shortcuts import render
from django.core.mail import BadHeaderError, send_mail
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import View
from django.template import loader
from ozone.mytools import CSVtoTuple
from customer.models import CustomerProfile


class SendMailView(View):

    def get(self, request):
        choice = request.GET['radioMail']
        if choice == '1':
            context = {
                'title': 'first mail'
            }
        elif choice == '2':
            context = {
                'title': 'second mail'
            }
        elif choice == '3':
            context = {
                'title': 'second mail'
            }
        elif choice == '4':
            context = {
                'title': 'second mail'
            }
        elif choice == '5':
            context = {
                'title': 'second mail'
            }
        elif choice == '6':
            context = {
                'title': 'second mail'
            }
        elif choice == '7':
            context = {
                'title': 'second mail'
            }
        elif choice == '8':
            context = {
                'title': 'second mail'
            }
        elif choice == '9':
            context = {
                'title': 'second mail'
            }
        elif choice == '10':
            context = {
                'title': 'second mail'
            }
        else:
            context = {
                'title': ''
            }
        return render(request, 'mails/mailing_form.html', context)

    def post(self, request):
        name = request.POST['name']
        closing_message = request.POST['closing']
        subject = request.POST['txtSubject']
        message = request.POST['message']
        from_email = request.user.email
        recipient = request.POST['toEmail']
        context = {
            'subject': subject,
            'name': name,
            'message': message,
            'closing_message': closing_message,
        }
        if request.GET['radioMail'] == '1':
            obj_list = CSVtoTuple(
                os.path.join(settings.BASE_DIR, 'customer/static/customers.csv')).csv_content(
                integer=(0,), decimal=(7,)
            )
            object = dict()
            objects = list()
            for record in obj_list:
                object['id'] = record[0]
                object['business'] = record[2]
                object['owner'] = record[1]
                object['cluster'] = record[6]
                object['address'] = record[3]
                object['mobile'] = record[4]
                object['email'] = record[5]
                object['type'] = record[8]
                object['sales'] = record[7]
                # 'frequency': record[]
            objects.append(object)
            context.update({
                'objects': objects,
            })
            html_message = loader.render_to_string('mails/customer_database.html',
                                                   context)
            # send_mail(subject, message, from_email, [recipient],
            #           html_message=html_message)
            return render(request, 'mails/customer_database.html', context)
        else:
            html_message = ''
            return HttpResponse('the second')

