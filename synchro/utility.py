from datetime import datetime
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db.models import Manager, Model
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet

import copy

class newQuerySet(QuerySet):
    fields_nk = []
    def natural_keys_list(self):
        return self.select_related().values_list(*self.fields_nk)

try:
    from batch_select.models import BatchQuerySet
    class newBatchQuerySet(BatchQuerySet):
        fields_nk = []
        def natural_keys_list(self):
            return self.select_related().values_list(*self.fields_nk)
except ImportError:
    newBatchQuerySet = newQuerySet
    BatchQuerySet = newQuerySet

class MetaIterBases(type):
    def __new__(cls, name, bases, dct):
        if isinstance(bases[0], (tuple, list)):
            bases = bases[0]
        return super(MetaIterBases, cls).__new__(cls, name, bases, dct)

class MetaChangeDefaultManager(MetaIterBases):
    def __new__(cls, name, bases, dct):
        if bases == (Manager,):
            bases = (NaturalManager,)
        return super(MetaChangeDefaultManager, cls).__new__(cls, name, bases, dct)

class NaturalManager(Manager):
    """
    Manager must be able to instantiate without arguments in order to work with M2M.
    Hence this machinery to store arguments in class.
    Somehow related to Django bug #13313.
    """
    allow_many = False

    def get_by_natural_key(self, *args):
        lookups = dict(zip(self.fields, args))
        try:
            return self.get(**lookups)
        except MultipleObjectsReturned:
            if self.allow_many:
                return self.filter(**lookups)[0]
            raise

    def get_query_set(self):
        fields = self.fields
        if isinstance(super(NaturalManager, self).get_query_set(), BatchQuerySet):
            newBatchQuerySet.fields_nk = fields
            qs = newBatchQuerySet(self.model, using=self._db)
        else:
            newQuerySet.fields_nk = fields
            qs = newQuerySet(self.model, using=self._db)

        if hasattr(self.model, '_mptt_meta'):
            return qs.order_by(self.model._mptt_meta.tree_id_attr, self.model._mptt_meta.left_attr)
        return qs

    def exists_by_natural_key(self, *args, **kwargs):
        lookups = dict(zip(self.fields, args))
        return self.filter(**lookups).exists()

    def natural_keys_list(self, *args, **kwargs):
        return self.get_query_set().filter(*args, **kwargs).natural_keys_list()

    def __new__(cls, *fields, **options):
        """
        Creates actual manager, which can be further subclassed and instantiated without arguments.
        """

        if not fields and hasattr(cls, 'fields') and hasattr(cls, 'allow_many'):
            # Class was already prepared.
            return super(NaturalManager, cls).__new__(cls)

        class BaseManagerClass(options.get('manager', Manager)):
            __metaclass__ = MetaChangeDefaultManager

        if not issubclass(BaseManagerClass, Manager):
            raise ValidationError(
                '%s manager class must be a subclass of django.db.models.Manager.'
                % BaseManagerClass.__name__)

        if cls.__name__ in ('RelatedManager', 'ManyRelatedManager'):
            BaseClasses = (cls, BaseManagerClass)
        else:
            BaseClasses = (BaseManagerClass)

        assert fields, 'No fields specified in %s constructor' % cls
        _fields = fields
        _allow_many = options.get('allow_many', False)

        class NewNaturalManager(BaseClasses):
            __metaclass__ = MetaIterBases

            fields = _fields
            allow_many = _allow_many

            def __init__(self, *args, **kwargs):
                # Intentionally ignore arguments
                args = self.fields if cls.__name__ in ('RelatedManager', 'ManyRelatedManager') else ()
                super(NewNaturalManager, self).__init__(*args)

        return NewNaturalManager()


class _NaturalKeyModelBase(ModelBase):
    def __new__(cls, name, bases, attrs):
        parents = [b for b in bases if isinstance(b, _NaturalKeyModelBase)]
        if not parents:
            return super(_NaturalKeyModelBase, cls).__new__(cls, name, bases, attrs)
        kwargs = {}
        if 'objects' in attrs:
            kwargs['manager'] = attrs['objects'].__class__
        kwargs.update(attrs.pop('_natural_manager_kwargs', {}))
        attrs['objects'] = NaturalManager(*attrs['_natural_key'], **kwargs)
        return super(_NaturalKeyModelBase, cls).__new__(cls, name, bases, attrs)


class NaturalKeyModel(Model):
    __metaclass__ = _NaturalKeyModelBase
    _natural_key = ()

    def natural_key(self):
        return tuple(getattr(self, field) for field in self._natural_key)

    class Meta:
        abstract = True


def reset_synchro():
    from models import ChangeLog, Reference, options
    options.last_check = datetime.now()
    ChangeLog.objects.all().delete()
    Reference.objects.all().delete()
