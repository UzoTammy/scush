from typing import Any
from django.utils.safestring import mark_safe

class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):

        response = self.get_response(request)
        
        return response
    
    def process_template_response(self, request, response):
        if hasattr(response, 'context_data'):
            # Add custom data to the context
            # if not request.user_agent.is_mobile: 
            response.context_data['naira'] = 'N'
            if request.GET.get('currency') == 'dollars':
                response.context_data['naira'] = '$'
            # else:
            #     response.context_data['naira'] = 'N'
        return response
    
    
