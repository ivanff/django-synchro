#-*- coding: utf-8 -*-

__author__ = 'ivan fedoseev'

from django.core.management.base import NoArgsCommand
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from synchro.settings import MODELS
from synchro.models import ChangeLog, Reference

import logging

logger = logging.getLogger(__name__)

class Command(NoArgsCommand):

    @transaction.commit_on_success
    def handle_noargs(self, **options):
        ctype_dict = dict(ContentType.objects.get_for_models(*MODELS))
        changelog = ChangeLog.objects.exclude(content_type__in=ctype_dict.values())
        reference = Reference.objects.exclude(content_type__in=ctype_dict.values())

        if changelog:
            logger.debug("Delete changelogs: %s", ', '.join(['[id: %s, ctype: %s, generic object: id:%s %s]' %\
                                 (obj.id, obj.content_type, obj.object.id, obj.object) for obj in changelog]))
        if reference:
            logger.debug("Delete reference: %s", ', '.join(['[id: %s, ctype: %s]' %\
                                 (obj.id, obj.content_type) for obj in reference]))
        changelog.delete()
        reference.delete()

        logger.info("Cleanup complit")