"""Simple dictionary-based internationalization (i18n) for pt, en, and it."""

SUPPORTED_LANGUAGES = ("pt", "en", "it")
DEFAULT_LANGUAGE = "pt"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "pt": {
        # General & Navigation
        "app_title": "Privio - Gestão de Compromissos & Reserva",
        "app_name": "Privio Commitments",
        "dashboard": "Dashboard",
        "swagger_api": "Swagger API",
        "footer_text": "Privio © 2026 - Gestão Financeira Inteligente com FastAPI, SQLAlchemy, Jinja2 & HTMX",
        # Language Switcher
        "lang_pt": "🇧🇷 Português",
        "lang_en": "🇺🇸 English",
        "lang_it": "🇮🇹 Italiano",
        # Metrics
        "suggested_monthly_title": "Total Sugerido do Mês",
        "monthly_label": "Mensal",
        "semiannual_label": "Semestral",
        "annual_label": "Anual",
        "per_month": "/mês",
        "active_commitments_count": "compromissos ativos considerados",
        "reserve_balance_title": "Saldo de Reserva",
        "total_deposits_label": "Depósitos",
        "total_paid_label": "Pagos",
        "reserve_stats": "{deposits} depósitos • {paid} pagos",
        "quick_actions_title": "Ações Rápidas",
        "new_commitment_btn": "➕ Novo Compromisso",
        "new_deposit_btn": "📥 Registrar Depósito",
        # Upcoming Occurrences Table
        "upcoming_title": "📅 Próximos Vencimentos",
        "upcoming_subtitle": "Projeção de recorrências futuras calculadas a partir da data de vencimento",
        "days_30": "30 dias",
        "days_60": "60 dias",
        "days_90": "90 dias",
        "th_due_date": "Data Prevista",
        "th_time_until": "Em quanto tempo",
        "th_description": "Descrição",
        "th_category": "Categoria",
        "th_recurrence": "Recorrência",
        "th_amount": "Valor",
        "th_status": "Status",
        "th_actions": "Ações",
        "today_badge": "Hoje",
        "tomorrow_badge": "Amanhã",
        "days_badge": "{days} dias",
        "estimate_badge": "Estimativa",
        "no_upcoming": "Nenhum compromisso encontrado para os próximos {days} dias.",
        # Commitments Table
        "commitments_title": "📋 Todos os Compromissos",
        "commitments_subtitle": "Cadastro e gerenciamento das regras de compromissos",
        "th_base_due_date": "Vencimento Base",
        "btn_mark_paid": "✓ Marcar Pago",
        "btn_reopen": "↩ Reabrir",
        "btn_edit": "✏️ Editar",
        "btn_delete": "🗑️",
        "confirm_delete_commitment": "Tem certeza que deseja excluir este compromisso?",
        "no_commitments": "Nenhum compromisso cadastrado ainda. Clique em '➕ Novo Compromisso' para adicionar.",
        # Modal & Form
        "modal_new_commitment": "➕ Novo Compromisso",
        "modal_edit_commitment": "✏️ Editar Compromisso",
        "modal_new_deposit": "📥 Registrar Depósito na Reserva",
        "field_description": "Descrição",
        "field_description_placeholder": "Ex: Aluguel, Internet, IPTU, Seguro Carro",
        "field_amount": "Valor (R$)",
        "field_due_date": "Data de Vencimento",
        "field_category": "Categoria",
        "field_category_placeholder": "Ex: Moradia, Saúde, Tech, Transporte",
        "field_recurrence": "Recorrência",
        "field_status": "Status",
        "field_is_estimate": "Valor é uma estimativa",
        "field_deposit_amount": "Valor Depositado (R$)",
        "field_deposit_date": "Data do Depósito",
        "field_deposit_note": "Observação / Descrição",
        "field_deposit_note_placeholder": "Ex: Transferência mensal de cobertura, Aporte extra",
        "btn_cancel": "Cancelar",
        "btn_save_changes": "Salvar Alterações",
        "btn_create_commitment": "Cadastrar Compromisso",
        "btn_save_deposit": "Salvar Depósito",
        # Enums
        "rec_none": "Nenhuma (Único)",
        "rec_weekly": "Semanal (7 dias)",
        "rec_monthly": "Mensal (todo mês)",
        "rec_semiannual": "Semestral (a cada 6 meses)",
        "rec_annual": "Anual (1 vez por ano)",
        "status_pending": "Pendente",
        "status_paid": "Pago",
        # Messages
        "msg_commitment_created": "Compromisso '{desc}' cadastrado com sucesso!",
        "msg_commitment_updated": "Compromisso '{desc}' atualizado com sucesso!",
        "msg_commitment_deleted": "Compromisso '{desc}' excluído com sucesso.",
        "msg_status_reopened": "Compromisso '{desc}' reaberto como pendente.",
        "msg_status_paid": "Compromisso '{desc}' marcado como pago!",
        "msg_deposit_created": "Depósito de R$ {amount} registrado com sucesso!",
    },
    "en": {
        # General & Navigation
        "app_title": "Privio - Commitment & Reserve Management",
        "app_name": "Privio Commitments",
        "dashboard": "Dashboard",
        "swagger_api": "Swagger API",
        "footer_text": "Privio © 2026 - Smart Financial Management with FastAPI, SQLAlchemy, Jinja2 & HTMX",
        # Language Switcher
        "lang_pt": "🇧🇷 Português",
        "lang_en": "🇺🇸 English",
        "lang_it": "🇮🇹 Italiano",
        # Metrics
        "suggested_monthly_title": "Suggested Monthly Budget",
        "monthly_label": "Monthly",
        "semiannual_label": "Semiannual",
        "annual_label": "Annual",
        "per_month": "/mo",
        "active_commitments_count": "active commitments included",
        "reserve_balance_title": "Reserve Balance",
        "total_deposits_label": "Deposits",
        "total_paid_label": "Paid",
        "reserve_stats": "{deposits} deposits • {paid} paid",
        "quick_actions_title": "Quick Actions",
        "new_commitment_btn": "➕ New Commitment",
        "new_deposit_btn": "📥 Register Deposit",
        # Upcoming Occurrences Table
        "upcoming_title": "📅 Upcoming Due Dates",
        "upcoming_subtitle": "Future recurring occurrences projected from original due date",
        "days_30": "30 days",
        "days_60": "60 days",
        "days_90": "90 days",
        "th_due_date": "Due Date",
        "th_time_until": "Time Remaining",
        "th_description": "Description",
        "th_category": "Category",
        "th_recurrence": "Recurrence",
        "th_amount": "Amount",
        "th_status": "Status",
        "th_actions": "Actions",
        "today_badge": "Today",
        "tomorrow_badge": "Tomorrow",
        "days_badge": "{days} days",
        "estimate_badge": "Estimate",
        "no_upcoming": "No commitments found for the next {days} days.",
        # Commitments Table
        "commitments_title": "📋 All Commitments",
        "commitments_subtitle": "Configuration and management of commitment rules",
        "th_base_due_date": "Base Due Date",
        "btn_mark_paid": "✓ Mark Paid",
        "btn_reopen": "↩ Reopen",
        "btn_edit": "✏️ Edit",
        "btn_delete": "🗑️",
        "confirm_delete_commitment": "Are you sure you want to delete this commitment?",
        "no_commitments": "No commitments registered yet. Click '➕ New Commitment' to add one.",
        # Modal & Form
        "modal_new_commitment": "➕ New Commitment",
        "modal_edit_commitment": "✏️ Edit Commitment",
        "modal_new_deposit": "📥 Register Reserve Deposit",
        "field_description": "Description",
        "field_description_placeholder": "E.g.: Rent, Internet, Property Tax, Car Insurance",
        "field_amount": "Amount ($)",
        "field_due_date": "Due Date",
        "field_category": "Category",
        "field_category_placeholder": "E.g.: Housing, Health, Tech, Transport",
        "field_recurrence": "Recurrence",
        "field_status": "Status",
        "field_is_estimate": "Amount is an estimate",
        "field_deposit_amount": "Deposited Amount ($)",
        "field_deposit_date": "Deposit Date",
        "field_deposit_note": "Note / Description",
        "field_deposit_note_placeholder": "E.g.: Monthly reserve transfer, Extra contribution",
        "btn_cancel": "Cancel",
        "btn_save_changes": "Save Changes",
        "btn_create_commitment": "Create Commitment",
        "btn_save_deposit": "Save Deposit",
        # Enums
        "rec_none": "None (One-off)",
        "rec_weekly": "Weekly (7 days)",
        "rec_monthly": "Monthly (every month)",
        "rec_semiannual": "Semiannual (every 6 months)",
        "rec_annual": "Annual (once a year)",
        "status_pending": "Pending",
        "status_paid": "Paid",
        # Messages
        "msg_commitment_created": "Commitment '{desc}' created successfully!",
        "msg_commitment_updated": "Commitment '{desc}' updated successfully!",
        "msg_commitment_deleted": "Commitment '{desc}' deleted successfully.",
        "msg_status_reopened": "Commitment '{desc}' reopened as pending.",
        "msg_status_paid": "Commitment '{desc}' marked as paid!",
        "msg_deposit_created": "Deposit of ${amount} registered successfully!",
    },
    "it": {
        # General & Navigation
        "app_title": "Privio - Gestione Impegni & Riserva",
        "app_name": "Privio Commitments",
        "dashboard": "Dashboard",
        "swagger_api": "API Swagger",
        "footer_text": "Privio © 2026 - Gestione Finanziaria Intelligente con FastAPI, SQLAlchemy, Jinja2 & HTMX",
        # Language Switcher
        "lang_pt": "🇧🇷 Portoghese",
        "lang_en": "🇺🇸 Inglese",
        "lang_it": "🇮🇹 Italiano",
        # Metrics
        "suggested_monthly_title": "Totale Mensile Suggerito",
        "monthly_label": "Mensile",
        "semiannual_label": "Semestrale",
        "annual_label": "Annuale",
        "per_month": "/mese",
        "active_commitments_count": "impegni attivi considerati",
        "reserve_balance_title": "Saldo di Riserva",
        "total_deposits_label": "Depositi",
        "total_paid_label": "Pagati",
        "reserve_stats": "{deposits} depositi • {paid} pagati",
        "quick_actions_title": "Azioni Rapide",
        "new_commitment_btn": "➕ Nuovo Impegno",
        "new_deposit_btn": "📥 Registra Deposito",
        # Upcoming Occurrences Table
        "upcoming_title": "📅 Prossime Scadenze",
        "upcoming_subtitle": "Proiezione delle ricorrenze future calcolate a partire dalla data di scadenza",
        "days_30": "30 giorni",
        "days_60": "60 giorni",
        "days_90": "90 giorni",
        "th_due_date": "Data Prevista",
        "th_time_until": "Tempo Rimanente",
        "th_description": "Descrizione",
        "th_category": "Categoria",
        "th_recurrence": "Ricorrenza",
        "th_amount": "Importo",
        "th_status": "Stato",
        "th_actions": "Azioni",
        "today_badge": "Oggi",
        "tomorrow_badge": "Domani",
        "days_badge": "{days} giorni",
        "estimate_badge": "Stima",
        "no_upcoming": "Nessun impegno trovato per i prossimi {days} giorni.",
        # Commitments Table
        "commitments_title": "📋 Tutti gli Impegni",
        "commitments_subtitle": "Configurazione e gestione delle regole degli impegni",
        "th_base_due_date": "Scadenza Base",
        "btn_mark_paid": "✓ Segna Pagato",
        "btn_reopen": "↩ Riapri",
        "btn_edit": "✏️ Modifica",
        "btn_delete": "🗑️",
        "confirm_delete_commitment": "Sei sicuro di voler eliminare questo impegno?",
        "no_commitments": "Nessun impegno registrato. Clicca su '➕ Nuovo Impegno' per aggiungere.",
        # Modal & Form
        "modal_new_commitment": "➕ Nuovo Impegno",
        "modal_edit_commitment": "✏️ Modifica Impegno",
        "modal_new_deposit": "📥 Registra Deposito Riserva",
        "field_description": "Descrizione",
        "field_description_placeholder": "Es: Affitto, Internet, Tasse, Assicurazione Auto",
        "field_amount": "Importo (€)",
        "field_due_date": "Data di Scadenza",
        "field_category": "Categoria",
        "field_category_placeholder": "Es: Alloggio, Salute, Tech, Trasporti",
        "field_recurrence": "Ricorrenza",
        "field_status": "Stato",
        "field_is_estimate": "L'importo è una stima",
        "field_deposit_amount": "Importo Depositato (€)",
        "field_deposit_date": "Data del Deposito",
        "field_deposit_note": "Nota / Descrizione",
        "field_deposit_note_placeholder": "Es: Trasferimento mensile, Quota straordinaria",
        "btn_cancel": "Annulla",
        "btn_save_changes": "Salva Modifiche",
        "btn_create_commitment": "Crea Impegno",
        "btn_save_deposit": "Salva Deposito",
        # Enums
        "rec_none": "Nessuna (Singolo)",
        "rec_weekly": "Settimanale (7 giorni)",
        "rec_monthly": "Mensile (ogni mese)",
        "rec_semiannual": "Semestrale (ogni 6 mesi)",
        "rec_annual": "Annuale (1 volta all'anno)",
        "status_pending": "In attesa",
        "status_paid": "Pagato",
        # Messages
        "msg_commitment_created": "Impegno '{desc}' creato con successo!",
        "msg_commitment_updated": "Impegno '{desc}' aggiornato con successo!",
        "msg_commitment_deleted": "Impegno '{desc}' eliminato con successo.",
        "msg_status_reopened": "Impegno '{desc}' riaperto in attesa.",
        "msg_status_paid": "Impegno '{desc}' contrassegnato come pagato!",
        "msg_deposit_created": "Deposito di € {amount} registrato con successo!",
    },
}


def normalize_lang(lang: str | None) -> str:
    """Normalize language code to one of the supported languages, defaulting to 'pt'."""
    if not lang:
        return DEFAULT_LANGUAGE
    code = lang.strip().lower()
    if code in SUPPORTED_LANGUAGES:
        return code
    # Check 2-letter prefix (e.g. en-US -> en)
    prefix = code[:2]
    if prefix in SUPPORTED_LANGUAGES:
        return prefix
    return DEFAULT_LANGUAGE


def get_translations(lang: str | None = None) -> dict[str, str]:
    """Retrieve full translation dictionary for the selected language."""
    code = normalize_lang(lang)
    return TRANSLATIONS.get(code, TRANSLATIONS[DEFAULT_LANGUAGE])


def t(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Translate a given key for the specified language, interpolating any kwargs."""
    code = normalize_lang(lang)
    trans = TRANSLATIONS.get(code, TRANSLATIONS[DEFAULT_LANGUAGE])
    template = trans.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
