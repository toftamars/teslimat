from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class DeliveryDocument(models.Model):
    _name = 'delivery.document'
    _description = 'Teslimat Belgesi'
    _order = 'delivery_date desc, name desc'
    _rec_name = 'name'

    name = fields.Char('Teslimat No', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, default='/')
    
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('ready', 'Hazır'),
        ('on_road', 'Yolda'),
        ('delivered', 'Teslim Edildi'),
        ('cancelled', 'İptal')
    ], string='Durum', default='draft', tracking=True)

    # Transfer Belgesi Referansı
    picking_id = fields.Many2one('stock.picking', string='Transfer Belgesi', 
                                required=True, readonly=True,
                                states={'draft': [('readonly', False)]})
    
    # Planlama ilişkisi
    planning_id = fields.Many2one('delivery.planning', string='Teslimat Planlaması',
                                 readonly=True, states={'draft': [('readonly', False)]})
    
    # Müşteri Bilgileri (Transfer belgesinden otomatik)
    partner_id = fields.Many2one('res.partner', string='Müşteri',
                                related='picking_id.partner_id', store=True)
    partner_phone = fields.Char('Telefon', related='partner_id.phone', store=True)
    partner_mobile = fields.Char('Mobil', related='partner_id.mobile', store=True)
    
    # Adres Bilgileri
    delivery_address = fields.Text('Teslimat Adresi',
                                  related='picking_id.partner_id.contact_address', store=True)
    district = fields.Char('İlçe', compute='_compute_district', store=True)
    
    # Teslimat Detayları
    delivery_date = fields.Date('Teslimat Tarihi', required=True,
                               readonly=True, states={'draft': [('readonly', False)]})
    
    vehicle_type = fields.Selection([
        ('anadolu', 'Anadolu Yakası'),
        ('avrupa', 'Avrupa Yakası'),
        ('kucuk_arac_1', 'Küçük Araç 1'),
        ('kucuk_arac_2', 'Küçük Araç 2'),
        ('ek_arac', 'Ek Araç')
    ], string='Araç Seçimi', required=True,
       readonly=True, states={'draft': [('readonly', False)]})
    
    # Ürün Bilgileri (Transfer belgesinden)
    move_lines = fields.One2many('stock.move', related='picking_id.move_lines',
                                string='Ürün Hareketleri', readonly=True)
    
    # Rota ve Harita
    route_info = fields.Text('Rota Bilgisi')
    map_url = fields.Char('Harita URL')
    
    # SMS Durumu
    sms_sent_on_road = fields.Boolean('Yolda SMS Gönderildi', default=False)
    sms_sent_delivered = fields.Boolean('Teslim SMS Gönderildi', default=False)
    
    # Sistem Alanları
    create_date = fields.Datetime('Oluşturma Tarihi', readonly=True)
    create_uid = fields.Many2one('res.users', 'Oluşturan', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('delivery.document') or '/'
        return super(DeliveryDocument, self).create(vals)

    @api.depends('partner_id')
    def _compute_district(self):
        for record in self:
            if record.partner_id and record.partner_id.city:
                record.district = record.partner_id.city
            else:
                record.district = ''

    @api.constrains('delivery_date', 'district')
    def _check_delivery_date_district(self):
        """İlçe ve tarih uyumluluğunu kontrol et"""
        for record in self:
            if record.delivery_date and record.district:
                weekday = record.delivery_date.weekday()  # 0=Pazartesi, 6=Pazar
                
                # Pazar günü kontrolü
                if weekday == 6:  # Pazar
                    raise ValidationError(_('Pazar günleri teslimat yapılamaz!'))
                
                # İlçe-gün uyumluluğu kontrolü
                if not self._check_district_day_compatibility(record.district, weekday):
                    allowed_days = self._get_allowed_days_for_district(record.district)
                    raise ValidationError(
                        _('"%s" ilçesi için seçilen gün uygun değil. Uygun günler: %s') 
                        % (record.district, ', '.join(allowed_days))
                    )

    @api.constrains('delivery_date', 'vehicle_type')
    def _check_daily_delivery_limit(self):
        """Günlük teslimat limitini kontrol et"""
        for record in self:
            if record.delivery_date and record.vehicle_type:
                # Sınırsız teslimat grubundaki kullanıcıları kontrol et
                if self.env.user.has_group('delivery_management.group_delivery_unlimited'):
                    continue
                
                # Aynı gün ve araç için teslimat sayısını say
                delivery_count = self.search_count([
                    ('delivery_date', '=', record.delivery_date),
                    ('vehicle_type', '=', record.vehicle_type),
                    ('state', 'in', ['ready', 'on_road', 'delivered']),
                    ('id', '!=', record.id)
                ])
                
                if delivery_count >= 7:
                    raise ValidationError(
                        _('Bu araç için günlük maksimum 7 teslimat limiti aşıldı!')
                    )

    def _check_district_day_compatibility(self, district, weekday):
        """İlçe ve gün uyumluluğunu kontrol et"""
        # Anadolu Yakası İlçeleri
        anadolu_districts = {
            0: ['Maltepe', 'Kartal', 'Pendik', 'Tuzla'],  # Pazartesi
            1: ['Üsküdar', 'Kadıköy', 'Ataşehir', 'Ümraniye'],  # Salı
            2: ['Üsküdar', 'Kadıköy', 'Ataşehir', 'Ümraniye'],  # Çarşamba
            3: ['Üsküdar', 'Kadıköy', 'Ataşehir', 'Ümraniye'],  # Perşembe
            4: ['Maltepe', 'Kartal', 'Pendik', 'Sultanbeyli'],  # Cuma
            5: ['Sancaktepe', 'Çekmeköy', 'Beykoz', 'Şile'],  # Cumartesi
        }
        
        # Avrupa Yakası İlçeleri
        avrupa_districts = {
            0: ['Beyoğlu', 'Şişli', 'Beşiktaş', 'Kağıthane'],  # Pazartesi
            1: ['Sarıyer', 'Bakırköy', 'Bahçelievler', 'Güngören', 'Esenler', 'Bağcılar'],  # Salı
            2: ['Beyoğlu', 'Şişli', 'Beşiktaş', 'Kağıthane'],  # Çarşamba
            3: ['Eyüpsultan', 'Gaziosmanpaşa', 'Küçükçekmece', 'Avcılar', 'Başakşehir', 'Sultangazi', 'Arnavutköy'],  # Perşembe
            4: ['Fatih', 'Zeytinburnu', 'Bayrampaşa'],  # Cuma
            5: ['Esenyurt', 'Beylikdüzü', 'Silivri', 'Çatalca'],  # Cumartesi
        }
        
        # Tüm izinli ilçeleri birleştir
        all_allowed_districts = anadolu_districts.get(weekday, []) + avrupa_districts.get(weekday, [])
        
        return district in all_allowed_districts

    def _get_allowed_days_for_district(self, district):
        """İlçe için izinli günleri getir"""
        district_day_mapping = {
            # Anadolu Yakası
            'Maltepe': ['Pazartesi', 'Cuma'],
            'Kartal': ['Pazartesi', 'Cuma'],
            'Pendik': ['Pazartesi', 'Cuma'],
            'Tuzla': ['Pazartesi'],
            'Sultanbeyli': ['Cuma'],
            'Üsküdar': ['Salı', 'Çarşamba', 'Perşembe'],
            'Kadıköy': ['Salı', 'Çarşamba', 'Perşembe'],
            'Ataşehir': ['Salı', 'Çarşamba', 'Perşembe'],
            'Ümraniye': ['Salı', 'Çarşamba', 'Perşembe'],
            'Sancaktepe': ['Cumartesi'],
            'Çekmeköy': ['Cumartesi'],
            'Beykoz': ['Cumartesi'],
            'Şile': ['Cumartesi'],
            
            # Avrupa Yakası
            'Beyoğlu': ['Pazartesi', 'Çarşamba'],
            'Şişli': ['Pazartesi', 'Çarşamba'],
            'Beşiktaş': ['Pazartesi', 'Çarşamba'],
            'Kağıthane': ['Pazartesi', 'Çarşamba'],
            'Sarıyer': ['Salı'],
            'Bakırköy': ['Salı'],
            'Bahçelievler': ['Salı'],
            'Güngören': ['Salı'],
            'Esenler': ['Salı'],
            'Bağcılar': ['Salı'],
            'Eyüpsultan': ['Perşembe'],
            'Gaziosmanpaşa': ['Perşembe'],
            'Küçükçekmece': ['Perşembe'],
            'Avcılar': ['Perşembe'],
            'Başakşehir': ['Perşembe'],
            'Sultangazi': ['Perşembe'],
            'Arnavutköy': ['Perşembe'],
            'Fatih': ['Cuma'],
            'Zeytinburnu': ['Cuma'],
            'Bayrampaşa': ['Cuma'],
            'Esenyurt': ['Cumartesi'],
            'Beylikdüzü': ['Cumartesi'],
            'Silivri': ['Cumartesi'],
            'Çatalca': ['Cumartesi'],
        }
        
        return district_day_mapping.get(district, [])

    def action_confirm(self):
        """Onayla butonu - Taslaktan Hazır durumuna geçir"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Sadece taslak durumundaki belgeler onaylanabilir!'))
            
            if not record.delivery_date:
                raise UserError(_('Teslimat tarihi seçilmelidir!'))
            
            if not record.vehicle_type:
                raise UserError(_('Araç seçimi yapılmalıdır!'))
            
            record.state = 'ready'

    def action_on_road(self):
        """Yolda butonu - Hazır durumundan Yolda durumuna geçir ve SMS gönder"""
        for record in self:
            if record.state != 'ready':
                raise UserError(_('Sadece hazır durumundaki belgeler yola çıkarılabilir!'))
            
            record.state = 'on_road'
            
            # SMS gönder
            if not record.sms_sent_on_road:
                record._send_sms_on_road()
                record.sms_sent_on_road = True

    def action_delivered(self):
        """Tamamla butonu - Yolda durumundan Teslim Edildi durumuna geçir ve SMS gönder"""
        for record in self:
            if record.state != 'on_road':
                raise UserError(_('Sadece yolda olan belgeler tamamlanabilir!'))
            
            record.state = 'delivered'
            
            # SMS gönder
            if not record.sms_sent_delivered:
                record._send_sms_delivered()
                record.sms_sent_delivered = True

    def action_cancel(self):
        """İptal butonu"""
        for record in self:
            if record.state in ['delivered']:
                raise UserError(_('Teslim edilmiş belgeler iptal edilemez!'))
            record.state = 'cancelled'

    def action_reset_to_draft(self):
        """Taslağa Dönüştür"""
        for record in self:
            record.state = 'draft'
            record.sms_sent_on_road = False
            record.sms_sent_delivered = False

    def _send_sms_on_road(self):
        """Yolda SMS'i gönder"""
        if self.partner_phone or self.partner_mobile:
            phone = self.partner_mobile or self.partner_phone
            message = _('Sayın %s, siparişiniz yola çıkmıştır. Teslimat belgesi: %s') % (
                self.partner_id.name, self.name)
            
            # SMS gönderimi (mevcut SMS kurgusuna entegre)
            try:
                self.env['sms.sms'].create({
                    'number': phone,
                    'body': message,
                    'partner_id': self.partner_id.id,
                }).send()
                _logger.info('Yolda SMS gönderildi: %s -> %s', self.name, phone)
            except Exception as e:
                _logger.error('SMS gönderimi hatası: %s', str(e))

    def _send_sms_delivered(self):
        """Teslim edildi SMS'i gönder"""
        if self.partner_phone or self.partner_mobile:
            phone = self.partner_mobile or self.partner_phone
            message = _('Sayın %s, teslimatınız tamamlanmıştır. Teşekkürler. Teslimat belgesi: %s') % (
                self.partner_id.name, self.name)
            
            # SMS gönderimi (mevcut SMS kurgusuna entegre)
            try:
                self.env['sms.sms'].create({
                    'number': phone,
                    'body': message,
                    'partner_id': self.partner_id.id,
                }).send()
                _logger.info('Teslim edildi SMS gönderildi: %s -> %s', self.name, phone)
            except Exception as e:
                _logger.error('SMS gönderimi hatası: %s', str(e))

    def action_view_picking(self):
        """Transfer belgesini görüntüle"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfer Belgesi'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'target': 'current',
        }