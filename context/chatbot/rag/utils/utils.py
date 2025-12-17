from rest_framework.response import Response

def error_response(message, status_code, extra_data=None):
    response_data = {"message": message}
    if extra_data:
        response_data.update(extra_data)
    return Response(response_data, status=status_code)

def success_response(message, data=None):
    response_data = {"message": message}
    if data:
        response_data.update({"data": data})
    return Response(response_data)

def parse_request_body(request):
    try:
        return request.data
    except Exception as e:
        return error_response("Invalid request body", 400) 