{
    'name': 'Teslimat Yönetimi',
    'version': '15.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Transfer belgelerinden otomatik teslimat belgesi oluşturma ve yönetimi',
    'description': """
Teslimat Yönetimi Modülü
========================
* Transfer belgelerinden otomatik teslimat belgesi oluşturma
* İlçe bazlı teslimat günleri planlaması
* SMS entegrasyonu ile müşteri bilgilendirme
* Araç ve rota yönetimi
* Günlük teslimat limiti kontrolü
* Rota optimizasyonu ve harita entegrasyonu
* Detaylı raporlama ve analiz
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'stock',
        'base',
        'contacts',
        'sms',
        'fleet',
        'web_google_maps',
    ],
    'data': [
        'security/delivery_security.xml',
        'security/ir.model.access.csv',
        'data/delivery_data.xml',
        'views/delivery_document_views.xml',
        'views/delivery_planning_views.xml',
        'views/delivery_route_views.xml',
        'views/delivery_report_views.xml',
        'views/stock_picking_views.xml',
        'views/delivery_menus.xml',
        'wizard/delivery_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['googlemaps'],
    },
}