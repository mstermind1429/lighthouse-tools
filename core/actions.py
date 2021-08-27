import pandas as pd

from django.http import HttpResponse
from django.db.models import Func


class Round(Func):
    function = 'ROUND'
    template = "%(function)s(%(expressions)s::numeric, 2)"


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/xlsx')
        response['Content-Disposition'] = 'attachment; filename={}.xlsx'.format(meta)

        data = {}
        for obj in queryset:
            for field in field_names:
                if field in data:
                    data[field].append(getattr(obj, field))
                else:
                    data[field] = [getattr(obj, field)]

        writer = pd.ExcelWriter(response, engine='xlsxwriter')
        df = pd.DataFrame(data=data)
        df['created_at'] = df['created_at'].apply(lambda a: pd.to_datetime(a).date())
        df['updated_at'] = df['updated_at'].apply(lambda a: pd.to_datetime(a).date())
        df.to_excel(writer, sheet_name='results', index=False)
        writer.save()

        return response

    export_as_csv.short_description = "Export Selected as CSV"


class CorrelationExport:
    def export_correlation(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.xlsx'.format(meta)

        data = {}
        for obj in queryset:
            for field in field_names:
                if field in data:
                    data[field].append(getattr(obj, field))
                else:
                    data[field] = [getattr(obj, field)]

        writer = pd.ExcelWriter(response, engine='xlsxwriter')
        df = pd.DataFrame(data=data)
        features = ['position', 'cumulative_ls', 'largest_cp', 'max_potential_fid']
        new_df = df[features].corr()
        new_df.to_excel(writer, sheet_name='correlation', index=True)
        writer.save()

        return response

    export_correlation.short_description = "Correlation Export"
