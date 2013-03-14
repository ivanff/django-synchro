from django.conf.urls import patterns, url

from views import synchro, reset


urlpatterns = patterns('',
    url(r'^reset/$', reset, name='reset'),
    url(r'^$', synchro, name='synchro'),
)
