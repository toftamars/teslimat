from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class DeliveryDistrictDay(models.Model):
    _name = 'delivery.district.day'
    _description = 'İlçe Teslimat Günleri'
    _order = 'district_name, weekday'

    name = fields.Char('Ad', compute='_compute_name', store=True)
    district_name = fields.Char('İlçe Adı', required=True)
    weekday = fields.Selection([
        (0, 'Pazartesi'),
        (1, 'Salı'),
        (2, 'Çarşamba'),
        (3, 'Perşembe'),
        (4, 'Cuma'),
        (5, 'Cumartesi'),
        (6, 'Pazar')
    ], string='Gün', required=True)
    is_active = fields.Boolean('Aktif', default=True)
    max_delivery_count = fields.Integer('Maksimum Teslimat Sayısı', default=7)
    notes = fields.Text('Notlar')

    _sql_constraints = [
        ('district_weekday_uniq', 'unique(district_name, weekday)',
         'Bu ilçe için bu gün zaten tanımlanmış!')
    ]

    @api.depends('district_name', 'weekday')
    def _compute_name(self):
        weekday_names = dict(self._fields['weekday'].selection)
        for record in self:
            record.name = f"{record.district_name} - {weekday_names[record.weekday]}"

    @api.constrains('weekday')
    def _check_weekday(self):
        for record in self:
            if record.weekday == 6:  # Pazar
                raise ValidationError(_('Pazar günleri teslimat yapılamaz!'))

    @api.model
    def get_allowed_days_for_district(self, district_name):
        """İlçe için izinli günleri getir"""
        records = self.search([
            ('district_name', '=', district_name),
            ('is_active', '=', True)
        ])
        return records.mapped('weekday')

    @api.model
    def check_district_day_compatibility(self, district_name, weekday):
        """İlçe ve gün uyumluluğunu kontrol et"""
        return bool(self.search([
            ('district_name', '=', district_name),
            ('weekday', '=', weekday),
            ('is_active', '=', True)
        ], limit=1))

    @api.model
    def get_max_delivery_count(self, district_name, weekday):
        """İlçe ve gün için maksimum teslimat sayısını getir"""
        record = self.search([
            ('district_name', '=', district_name),
            ('weekday', '=', weekday),
            ('is_active', '=', True)
        ], limit=1)
        return record.max_delivery_count if record else 7  # Varsayılan 7 