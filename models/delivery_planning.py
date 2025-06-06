# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class DeliveryPlanning(models.Model):
    _name = 'delivery.planning'
    _description = 'Teslimat Planlaması'
    _order = 'planning_date desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Plan No', required=True, copy=False, readonly=True,
                      states={'draft': [('readonly', False)]}, default='/')
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('confirmed', 'Onaylandı'),
        ('in_progress', 'Devam Ediyor'),
        ('done', 'Tamamlandı'),
        ('cancelled', 'İptal')
    ], string='Durum', default='draft', tracking=True)

    planning_date = fields.Date('Planlama Tarihi', required=True, tracking=True)
    vehicle_type = fields.Selection([
        ('anadolu', 'Anadolu Yakası'),
        ('avrupa', 'Avrupa Yakası'),
        ('kucuk_arac_1', 'Küçük Araç 1'),
        ('kucuk_arac_2', 'Küçük Araç 2'),
        ('ek_arac', 'Ek Araç')
    ], string='Araç Tipi', required=True, tracking=True)

    delivery_ids = fields.One2many('delivery.document', 'planning_id', string='Teslimat Belgeleri')
    delivery_count = fields.Integer('Teslimat Sayısı', compute='_compute_delivery_count', store=True)
    
    total_distance = fields.Float('Toplam Mesafe (km)', tracking=True)
    estimated_duration = fields.Float('Tahmini Süre (dk)', tracking=True)
    
    notes = fields.Text('Notlar', tracking=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('delivery.planning') or '/'
        return super().create(vals)

    @api.depends('delivery_ids')
    def _compute_delivery_count(self):
        for record in self:
            record.delivery_count = len(record.delivery_ids)

    @api.constrains('planning_date', 'vehicle_type')
    def _check_planning_date(self):
        for record in self:
            if record.planning_date:
                # Pazar günü kontrolü
                if record.planning_date.weekday() == 6:
                    raise ValidationError(_('Pazar günleri teslimat planlaması yapılamaz!'))
                
                # Geçmiş tarih kontrolü
                if record.planning_date < fields.Date.context_today(self):
                    raise ValidationError(_('Geçmiş tarih için planlama yapılamaz!'))

    def action_confirm(self):
        """Planı onayla"""
        for record in self:
            if not record.delivery_ids:
                raise ValidationError(_('Planlama için en az bir teslimat belgesi eklenmelidir!'))
            
            # Teslimat belgelerini kontrol et
            for delivery in record.delivery_ids:
                if delivery.state != 'ready':
                    raise ValidationError(_('Tüm teslimat belgeleri "Hazır" durumunda olmalıdır!'))
            
            record.state = 'confirmed'

    def action_start(self):
        """Planlamayı başlat"""
        for record in self:
            if record.state != 'confirmed':
                raise ValidationError(_('Sadece onaylanmış planlamalar başlatılabilir!'))
            
            # Teslimat belgelerini "Yolda" durumuna geçir
            record.delivery_ids.write({'state': 'on_road'})
            record.state = 'in_progress'

    def action_done(self):
        """Planlamayı tamamla"""
        for record in self:
            if record.state != 'in_progress':
                raise ValidationError(_('Sadece devam eden planlamalar tamamlanabilir!'))
            
            # Tüm teslimatların tamamlandığını kontrol et
            if any(delivery.state != 'delivered' for delivery in record.delivery_ids):
                raise ValidationError(_('Tüm teslimatlar tamamlanmadan planlama bitirilemez!'))
            
            record.state = 'done'

    def action_cancel(self):
        """Planlamayı iptal et"""
        for record in self:
            if record.state in ['done']:
                raise ValidationError(_('Tamamlanmış planlamalar iptal edilemez!'))
            
            # Teslimat belgelerini "Hazır" durumuna geri al
            record.delivery_ids.write({'state': 'ready'})
            record.state = 'cancelled'

    def action_reset_to_draft(self):
        """Taslağa dönüştür"""
        for record in self:
            record.state = 'draft'

    def action_view_deliveries(self):
        """Teslimat belgelerini görüntüle"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Teslimat Belgeleri'),
            'view_mode': 'tree,form',
            'res_model': 'delivery.document',
            'domain': [('planning_id', '=', self.id)],
            'context': {'create': False},
        }

class DeliveryDistrictDay(models.Model):
    _name = 'delivery.district.day'
    _description = 'İlçe-Gün Eşleştirmesi'
    _rec_name = 'district'

    planning_id = fields.Many2one('delivery.planning', string='Planlama', 
                                 required=True, ondelete='cascade')
    
    district = fields.Char('İlçe', required=True)
    
    day = fields.Selection([
        ('monday', 'Pazartesi'),
        ('tuesday', 'Salı'),
        ('wednesday', 'Çarşamba'),
        ('thursday', 'Perşembe'),
        ('friday', 'Cuma'),
        ('saturday', 'Cumartesi'),
    ], string='Gün', required=True)
    
    region = fields.Selection([
        ('anadolu', 'Anadolu Yakası'),
        ('avrupa', 'Avrupa Yakası'),
    ], string='Bölge', required=True)
    
    _sql_constraints = [
        ('unique_district_day', 'unique(district, day)', 
         'Aynı ilçe için aynı gün birden fazla kez tanımlanamaz!'),
    ]