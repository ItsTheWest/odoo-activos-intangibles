# Intangible Assets Management (`gestion_activos_intangibles`)

Professional Odoo module designed to manage and track intangible assets within the organization.

## 📝 Description
This module provides a robust framework for registering, categorizing, and monitoring intangible assets. It is designed following Clean Architecture principles to ensure scalability and maintainability.

## 🚀 Key Features
*   **Asset Registration**: Complete lifecycle management for intangible assets.
*   **Categorization**: Hierarchical classification for better reporting.
*   **Security Roles**: Granular access control based on Odoo security groups.
*   **Audit Trail**: Detailed tracking of changes and movements.

## 🛠 Installation
1. Clone this repository into your Odoo `addons` directory.
2. Update the `addons_path` in your configuration file if necessary.
3. Restart the Odoo server.
4. Log in as an administrator.
5. Go to **Apps** and click **Update Apps List**.
6. Search for `gestion_activos_intangibles` and click **Install**.

## 💻 Technical Details
*   **Odoo Version**: Designed for modern Odoo versions (15.0+).
*   **Dependencies**: Depends on the `base` module.
*   **Architecture**:
    *   `models/`: Business logic and data schema.
    *   `views/`: XML definitions for the UI.
    *   `security/`: Access rights and record rules.
    *   `controllers/`: (Optional) Web and API endpoints.
