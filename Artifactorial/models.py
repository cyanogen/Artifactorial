from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

import binascii
import datetime
import os


def random_hash():
    """ Create a random string of size 32 """
    return binascii.b2a_hex(os.urandom(16))


@python_2_unicode_compatible
class AuthToken(models.Model):
    user = models.ForeignKey(User, blank=False)
    secret = models.TextField(max_length=32, unique=True, default=random_hash)
    description = models.TextField(null=False, blank=True)

    def __str__(self):
        return "%s (%s)" % (self.user.get_full_name(), self.description)


@python_2_unicode_compatible
class Directory(models.Model):
    path = models.CharField(max_length=300, null=False, blank=False)
    user = models.ForeignKey(User, null=True, blank=True)
    group = models.ForeignKey(Group, null=True, blank=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Directories'

    def clean(self):
        """
        Artifacts should be owned by one group or one user, not both.
        """
        if self.user is not None and self.group is not None:
            raise ValidationError("Cannot be owned by user and group")
        if self.user is None and self.group is None and not self.is_public:
            raise ValidationError("An anonymous directory should be public")
        if not os.path.normpath(self.path) == self.path:
            raise ValidationError({'path': ['Expecting a normalized path and '
                                            'no leading slashes']})
        if not os.path.isabs(self.path):
            raise ValidationError({'path': ['Expecting an absolute path']})

    def __str__(self):
        if self.user is not None:
            return "%s (%s)" % (self.path, self.user.get_full_name())
        elif self.group is not None:
            return "%s (%s)" % (self.path, self.group)
        else:
            return "%s (anonymous)" % (self.path)

    def is_anonymous(self):
        return (self.user is None and self.group is None)

    def is_visible_to(self, user):
        if self.is_public:
            return True
        if self.user is not None:
            return self.user == user
        elif self.group is not None:
            return self.group in user.groups.all()
        else:
            return True


def get_path_name(instance, filename):
    base_path = ''
    if not instance.is_permanent:
        now = datetime.datetime.now()
        base_path = now.strftime('%Y/%m/%d/%H/%M')
    return os.path.normpath('/'.join([instance.directory.path,
                                      base_path, filename])).strip('/')


@python_2_unicode_compatible
class Artifact(models.Model):
    path = models.FileField(upload_to=get_path_name)
    directory = models.ForeignKey(Directory, blank=False)
    is_permanent = models.BooleanField(default=False)

    def __str__(self):
        return self.path.name

    def is_visible_to(self, user):
        return self.directory.is_visible_to(user)
