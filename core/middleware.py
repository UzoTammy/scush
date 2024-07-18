from typing import Any

class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        
        response = self.get_response(request)
        
        return response
    
    def process_template_response(self, request, response):
        if hasattr(response, 'context_data'):
            # Add custom data to the context
            response.context_data['naira'] = chr(8358)
        return response
    
    