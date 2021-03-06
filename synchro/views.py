from cStringIO import StringIO

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.core.management import call_command

from models import options
from .utility import reset_synchro

@staff_member_required
def synchro(request):
    if 'synchro' in request.POST:
        so = StringIO()
        try:
            call_command('synchronize', stdout=so)
            messages.add_message(request, messages.INFO, so.getvalue())
        except Exception as e:
            msg = 'An error occured: %s (%s)' % (str(e), e.__class__.__name__)
            messages.add_message(request, messages.ERROR, msg)
        finally:
            so.close()
    return TemplateResponse(request, 'synchro.html', {'last': options.last_check})

@staff_member_required
def reset(request):
    reset_synchro()
    messages.add_message(request, messages.INFO, 'Reset synchro is done')
    return HttpResponseRedirect(reverse('synchro', current_app='synchro'))