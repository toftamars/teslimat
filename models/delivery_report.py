# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta

class DeliveryReport(models.Model):
    _name = 'delivery.report'
    _description = 'Teslimat Raporu'
    _auto = False
    _order = 'date desc'

    date = fields.Date('Tarih')
    district = fields.Char('İlçe')
    vehicle_type = fields.Char('Araç Tipi')
    delivery_count = fields.Integer('Teslimat Sayısı')
    total_distance = fields.Float('Toplam Mesafe (km)')
    total_duration = fields.Float('Toplam Süre (dk)')
    success_rate = fields.Float('Başarı Oranı (%)')
    avg_delivery_time = fields.Float('Ortalama Teslimat Süresi (dk)')

    def _select(self):
        return """
            SELECT
                row_number() OVER () as id,
                d.delivery_date as date,
                d.district,
                d.vehicle_type,
                COUNT(*) as delivery_count,
                COALESCE(r.total_distance, 0) as total_distance,
                COALESCE(r.total_duration, 0) as total_duration,
                CASE 
                    WHEN COUNT(*) > 0 THEN 
                        (COUNT(*) FILTER (WHERE d.state = 'delivered')::float / COUNT(*)::float) * 100 
                    ELSE 0 
                END as success_rate,
                CASE 
                    WHEN COUNT(*) > 0 THEN 
                        COALESCE(r.total_duration, 0) / COUNT(*)::float 
                    ELSE 0 
                END as avg_delivery_time
        """

    def _from(self):
        return """
            FROM delivery_document d
            LEFT JOIN delivery_route r ON r.planning_id = d.planning_id
        """

    def _group_by(self):
        return """
            GROUP BY
                d.delivery_date,
                d.district,
                d.vehicle_type,
                r.total_distance,
                r.total_duration
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._group_by()))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(DeliveryReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        return res 