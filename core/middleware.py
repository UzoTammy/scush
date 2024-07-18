from typing import Any

class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        
        response = self.get_response(request)
        
        return response
    
    # def process_template_response(self, request, response):
    #     if hasattr(response, 'context_data'):
    #         # Add custom data to the context
    #         response.context_data['custom_data'] = 'From Middleware'
    #     else:
    #         pass
    #     return response
    
    # def process_request(self, request):
    #     print('abc')
    #     return None
    
    # def process_response(self, request, response):
    #     print("Middleware process_response")
    #     # Optionally modify the response
    #     return response