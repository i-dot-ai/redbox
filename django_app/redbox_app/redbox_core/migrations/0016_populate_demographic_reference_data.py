from django.db import migrations


BUSINESS_UNITS = [
    "Prime Minister's Office",
    "Delivery Group",
    "National Security Secretariat",
    "Economic and Domestic Secretariat",
    "Propriety and Constitution Group",
    "Government in Parliament",
    "Joint Intelligence Organisation",
    "Intelligence and Security Committee",
    "Government Digital Service",
    "Central Digital and Data Office",
    "Government Communication Service",
    "Government Security Group",
    "UKSV",
    "Government Commercial and Grants Function",
    "Civil Service Human Resources",
    "Infrastructure and Projects Authority",
    "Office of Government Property",
    "Government Business Services",
    "Borders Unit",
    "Equality Hub",
    "Public Sector Fraud Authority",
    "CO Chief Operating Officer",
    "Flexible CS Pool",
    "CO People and Places",
    "CO Strategy, Finance, and Performance",
    "Central Costs",
    "CO HMT Commercial",
    "CO Digital",
    "Public Bodies and Priority Projects Unit",
    "Public Inquiry Response Unit",
    "CS Modernisation and Reform Unit",
    "Office for Veterans' Affairs",
    "Grenfell Inquiry",
    "Infected Blood Inquiry",
    "Covid Inquiry",
    "Civil Service Commission",
    "Equality and Human Rights Commission",
    "Government Property Agency",
    "Office of the Registrar of Consultant Lobbyists",
    "Crown Commercial Service",
    "Union and Constitution Group",
    "Geospatial Commission",
    "Commercial Models",
    "COP Presidency",
    "Inquiries Sponsorship Team",
    "Other",
]
GRADES = [
    "AA",
    "AO",
    "Deputy Director",
    "Director",
    "Director General",
    "EO",
    "G6",
    "G7",
    "HEO",
    "Perm Sec",
    "SEO",
    "Other",
]
PROFESSIONS = [
    "Analysis",
    "Commercial",
    "Communications",
    "Corporate finance",
    "Counter fraud",
    "Digital, data and technology",
    "Economics",
    "Finance",
    "Fraud, error, debts and grants",
    "Human resources",
    "Intelligence analysis",
    "Internal audit",
    "International trade",
    "Knowledge and information management",
    "Legal",
    "Medical",
    "Occupational psychology",
    "Operational delivery",
    "Operational research",
    "Planning",
    "Planning inspection",
    "Policy",
    "Project delivery",
    "Property",
    "Science and engineering",
    "Security",
    "Social research",
    "Statistics",
    "Tax",
    "Veterinary",
    "Other",
]


def populate_business_units(apps, schema_editor):
    BusinessUnit = apps.get_model('redbox_core', 'BusinessUnit')
    for name in BUSINESS_UNITS:
        BusinessUnit.objects.create(name=name)


def populate_grades(apps, schema_editor):
    UserGrade = apps.get_model('redbox_core', 'UserGrade')
    for name in GRADES:
        UserGrade.objects.create(name=name)


def populate_professions(apps, schema_editor):
    Profession = apps.get_model('redbox_core', 'Profession')
    for name in PROFESSIONS:
        Profession.objects.create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('redbox_core', '0015_add_demographic_data'),
    ]

    operations = [
        migrations.RunPython(populate_business_units),
        migrations.RunPython(populate_grades),
        migrations.RunPython(populate_professions),
    ]
