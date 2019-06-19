from django import forms

from tagging.forms import TagField


class GazetteSearchForm(forms.Form):
    search = forms.CharField(required=False, label='Search term')
    tag = TagField(required=False, label='Tags')
