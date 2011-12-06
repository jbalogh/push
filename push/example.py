import requests
from cornice.service import Service


queues = Service(name='queues', path='/example/queue/')


@queues.post()
def new_queue(request):
    queue = request.POST['queue']
    msg = request.POST['message']
    # TODO: set API key.
    title = 'Message from example.com'
    r = requests.post(queue, data={'title': title, 'body': msg})
