from django import forms


class GazetteSearchForm(forms.Form):
    search = forms.CharField(required=False, label='Search term')
