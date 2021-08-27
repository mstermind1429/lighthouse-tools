import datetime

from django.contrib.admin import SimpleListFilter


class LighthouseDateFilter(SimpleListFilter):
    title = 'Date'
    parameter_name = 'created_at'

    def lookups(self, request, model_admin):
        dates = [c.created_at.strftime('%Y-%m-%d') for c in model_admin.model.objects.all()]
        dates.sort(key=lambda date: datetime.datetime.strptime(date, '%Y-%m-%d'))
        dates = set(dates)
        return [(date, date) for date in dates]

    def queryset(self, request, queryset):
        if self.value():
            date = datetime.datetime.strptime(self.value(), '%Y-%m-%d')
            return queryset.filter(created_at__year=str(date.year),
                                   created_at__month=str(date.month),
                                   created_at__day=str(date.day))
        else:
            return queryset
