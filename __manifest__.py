{
    'name': "Gestión de Activos Intangibles",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Nelson Figueroa",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Contabilidad/Finanzas',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'account', 'hr_expense', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/data.xml',
        # views.xml MUST come before evidence_views.xml because the latter
        # references search and form views defined in the former.
        'views/views.xml',
        'views/activo_intangible_type_views.xml',
        'views/statistics_views.xml',
        'views/calendar_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gestion_activos_intangibles/static/src/css/calendar_custom.css',
        ],
    },
}
