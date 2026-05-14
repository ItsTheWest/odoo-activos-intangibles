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

        # ── LAYER 1: Core record views ────────────────────────────────────
        # Load order: form/list first so that actions in later files can
        # reference them by xml_id without forward-reference errors.
        'views/activo_intangible_form_view.xml',
        'views/activo_intangible_list_view.xml',

        # ── LAYER 2: Configuration / catalogue views ─────────────────────
        'views/activo_intangible_type_views.xml',

        # ── LAYER 3: Evidence UI (ir.attachment extensions) ───────────────
        'views/activo_intangible_attachment_views.xml',

        # ── LAYER 4: Wizard pop-up views ─────────────────────────────────
        'views/activo_intangible_wizard_views.xml',

        # ── LAYER 5: Analysis & reporting views ──────────────────────────
        'views/dashboard_views.xml',
        'views/calendar_views.xml',

        # ── LAYER 6: Navigation (menus + actions) ────────────────────────
        # MUST be last: every action and view xml_id referenced here must
        # already exist in the database before this file is processed.
        'views/activo_intangible_menus_actions.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gestion_activos_intangibles/static/src/css/calendar_custom.css',
            'gestion_activos_intangibles/static/src/css/dashboard_custom.css',
            # OWL templates must be registered BEFORE the JS modules that reference them.
            'gestion_activos_intangibles/static/src/xml/estado_bar_chart.xml',
            'gestion_activos_intangibles/static/src/xml/tipo_activo_pie_chart.xml',
            'gestion_activos_intangibles/static/src/js/estado_bar_chart.js',
            'gestion_activos_intangibles/static/src/js/tipo_activo_pie_chart.js',
        ],
    },
}
