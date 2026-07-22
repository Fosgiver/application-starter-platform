"""Graphical Windows wizard for creating application projects."""

from dataclasses import dataclass, replace
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import tkinter as tk
from tkinter import (
    filedialog,
    messagebox,
    ttk,
)
import webbrowser

from pydantic import ValidationError

from app.db.providers import (
    DatabaseProviderId,
    get_database_provider_profile,
)
from developer_setup import (
    DEFAULT_PUBLIC_BASE_URL,
    DeveloperSetupRequest,
    create_application_project,
    normalize_optional_argument,
    validate_destination_directory,
)


WINDOW_TITLE = "Application Starter Developer Setup"
WINDOW_SIZE = "920x700"

GOOGLE_APP_PASSWORDS_URL = (
    "https://myaccount.google.com/apppasswords"
)

ACCENT_COLOR = "#174A7E"
ACCENT_MID_COLOR = "#2F669A"
ACCENT_LIGHT_COLOR = "#E8F1FA"
SUCCESS_COLOR = "#258750"
SURFACE_COLOR = "#FFFFFF"
TEXT_COLOR = "#17212B"
MUTED_TEXT_COLOR = "#52606D"

STEP_NAMES = (
    "Project",
    "Access",
    "Email",
    "Database",
    "Review",
)

FIELD_LABELS = {
    "application_name": "Application name",
    "database_provider": "Database provider",
    "database_url": "Database URL",
    "destination": "Project folder",
    "gmail_address": "Gmail address",
    "gmail_app_password": "Gmail App Password",
    "public_base_url": "Application URL",
    "smtp_host": "SMTP host",
    "smtp_password": "SMTP password",
    "smtp_port": "SMTP port",
    "smtp_security": "SMTP security",
    "smtp_sender_email": "Sender email",
    "smtp_sender_name": "Sender name",
    "smtp_username": "SMTP username",
}


@dataclass(
    frozen=True,
    slots=True,
)
class DeveloperSetupFormData:
    destination: str
    application_name: str
    email_mode: str
    access_mode: str = "local"
    public_base_url: str = DEFAULT_PUBLIC_BASE_URL
    gmail_address: str = ""
    gmail_app_password: str = ""
    smtp_host: str = ""
    smtp_port: str = ""
    smtp_security: str = ""
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_sender_email: str = ""
    smtp_sender_name: str = ""
    database_provider: str = "sqlite"
    database_url: str = ""


def create_step_states(
    current_page_index: int,
) -> tuple[str, ...]:
    if not 0 <= current_page_index < len(STEP_NAMES):
        raise ValueError(
            "Current page index is outside the wizard."
        )

    return tuple(
        (
            "completed"
            if step_index < current_page_index
            else (
                "current"
                if step_index == current_page_index
                else "pending"
            )
        )
        for step_index in range(len(STEP_NAMES))
    )


def parse_optional_port(
    value: str,
) -> int | None:
    normalized_value = value.strip()

    if not normalized_value:
        return None

    try:
        return int(normalized_value)
    except ValueError as error:
        raise ValueError(
            "SMTP port must be a whole number."
        ) from error


def build_setup_request(
    form_data: DeveloperSetupFormData,
) -> DeveloperSetupRequest:
    email_mode = form_data.email_mode.strip()
    application_name = (
        form_data.application_name.strip()
    )
    destination_text = form_data.destination.strip()
    access_mode = form_data.access_mode.strip()

    if not destination_text:
        raise ValueError(
            "Project folder is required."
        )

    if access_mode == "local":
        public_base_url = DEFAULT_PUBLIC_BASE_URL
    elif access_mode == "public":
        public_base_url = (
            form_data.public_base_url.strip()
        )
    else:
        raise ValueError(
            "Application access mode is invalid."
        )

    gmail_address: str | None = None
    gmail_app_password: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_security: str | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender_email: str | None = None
    smtp_sender_name: str | None = None

    if email_mode == "gmail":
        gmail_address = normalize_optional_argument(
            form_data.gmail_address
        )
        gmail_app_password = (
            normalize_optional_argument(
                form_data.gmail_app_password
            )
        )
    elif email_mode == "smtp":
        smtp_host = normalize_optional_argument(
            form_data.smtp_host
        )
        smtp_port = parse_optional_port(
            form_data.smtp_port
        )
        smtp_security = normalize_optional_argument(
            form_data.smtp_security
        )
        smtp_username = normalize_optional_argument(
            form_data.smtp_username
        )
        smtp_password = normalize_optional_argument(
            form_data.smtp_password
        )
        smtp_sender_email = (
            normalize_optional_argument(
                form_data.smtp_sender_email
            )
        )
        smtp_sender_name = (
            normalize_optional_argument(
                form_data.smtp_sender_name
            )
        )

    return DeveloperSetupRequest(
        destination=(
            Path(destination_text)
            .expanduser()
            .resolve()
        ),
        application_name=application_name,
        email_mode=email_mode,
        gmail_address=gmail_address,
        gmail_app_password=gmail_app_password,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_security=smtp_security,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        smtp_sender_email=smtp_sender_email,
        smtp_sender_name=smtp_sender_name,
        database_provider=(
            form_data.database_provider.strip()
        ),
        database_url=normalize_optional_argument(
            form_data.database_url
        ),
        public_base_url=public_base_url,
    )


def format_validation_error(
    error: ValidationError,
) -> str:
    messages: list[str] = []

    for validation_error in error.errors(
        include_url=False
    ):
        location = validation_error.get(
            "loc",
            (),
        )
        field_name = (
            str(location[-1])
            if location
            else ""
        )
        field_label = FIELD_LABELS.get(
            field_name,
            field_name.replace("_", " ").title(),
        )
        message = str(
            validation_error.get(
                "msg",
                "Invalid value.",
            )
        )

        if message.startswith("Value error, "):
            message = message.removeprefix(
                "Value error, "
            )

        if field_label:
            messages.append(
                f"{field_label}: {message}"
            )
        else:
            messages.append(message)

    return "\n".join(messages)


def create_review_lines(
    request: DeveloperSetupRequest,
) -> tuple[str, ...]:
    provider_profile = (
        get_database_provider_profile(
            request.database_provider
        )
    )

    if request.email_mode == "console":
        email_summary = "Console (no SMTP delivery)"
    elif request.email_mode == "gmail":
        email_summary = (
            f"Gmail — {request.gmail_address} "
            "(App Password provided)"
        )
    else:
        authentication_summary = (
            "credentials provided"
            if request.smtp_username is not None
            else "no authentication"
        )
        email_summary = (
            f"Custom SMTP — {request.smtp_host}:"
            f"{request.smtp_port}, "
            f"{request.smtp_security}, "
            f"{authentication_summary}"
        )

    if request.database_url is None:
        database_summary = (
            f"{provider_profile.display_name} — "
            "automatic project-local database"
        )
    else:
        database_summary = (
            f"{provider_profile.display_name} — "
            "connection URL provided"
        )

    if request.public_base_url == DEFAULT_PUBLIC_BASE_URL:
        access_summary = (
            "Local only — "
            f"{request.public_base_url}"
        )
    else:
        access_summary = (
            "Public HTTPS — "
            f"{request.public_base_url}"
        )

    return (
        f"Application: {request.application_name}",
        f"Project folder: {request.destination}",
        f"Access: {access_summary}",
        f"Email: {email_summary}",
        f"Database: {database_summary}",
        "",
        (
            "The project will be created only if the selected "
            "destination does not contain existing files."
        ),
        (
            "Passwords and connection credentials will be "
            "written only to the generated .env file."
        ),
    )


class DeveloperSetupWizard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(840, 640)
        self.configure(background=SURFACE_COLOR)
        self.protocol(
            "WM_DELETE_WINDOW",
            self.cancel,
        )

        self.current_page_index = 0
        self.validated_request: (
            DeveloperSetupRequest | None
        ) = None
        self.result_queue: Queue[
            tuple[bool, str]
        ] = Queue()
        self.is_busy = False

        self._create_variables()
        self._configure_style()
        self._create_layout()
        self.show_page(0)

    def _create_variables(self) -> None:
        self.destination_var = tk.StringVar()
        self.application_name_var = tk.StringVar()
        self.access_mode_var = tk.StringVar(
            value="local"
        )
        self.public_base_url_var = tk.StringVar()
        self.email_mode_var = tk.StringVar(
            value="console"
        )
        self.gmail_address_var = tk.StringVar()
        self.gmail_app_password_var = tk.StringVar()
        self.smtp_host_var = tk.StringVar()
        self.smtp_port_var = tk.StringVar(
            value="587"
        )
        self.smtp_security_var = tk.StringVar(
            value="starttls"
        )
        self.smtp_username_var = tk.StringVar()
        self.smtp_password_var = tk.StringVar()
        self.smtp_sender_email_var = tk.StringVar()
        self.smtp_sender_name_var = tk.StringVar()
        self.show_email_passwords_var = (
            tk.BooleanVar(value=False)
        )
        self.database_url_var = tk.StringVar()
        self.show_database_url_var = (
            tk.BooleanVar(value=False)
        )
        self.database_example_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self.database_display_to_id: dict[
            str,
            str,
        ] = {}
        self.database_id_to_display: dict[
            str,
            str,
        ] = {}

        for provider_id in DatabaseProviderId:
            provider_profile = (
                get_database_provider_profile(
                    provider_id
                )
            )
            self.database_display_to_id[
                provider_profile.display_name
            ] = provider_id.value
            self.database_id_to_display[
                provider_id.value
            ] = provider_profile.display_name

        self.database_provider_var = tk.StringVar(
            value=self.database_id_to_display[
                DatabaseProviderId.SQLITE.value
            ]
        )

    def _configure_style(self) -> None:
        style = ttk.Style(self)

        if "vista" in style.theme_names():
            style.theme_use("vista")

        style.configure(
            "WizardTitle.TLabel",
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "WizardSubtitle.TLabel",
            font=("Segoe UI", 10),
            foreground="#4a4a4a",
        )
        style.configure(
            "Section.TLabel",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Status.TLabel",
            foreground=ACCENT_COLOR,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Wizard.TEntry",
            font=("Segoe UI", 11),
            padding=(8, 7),
        )
        style.configure(
            "Wizard.TCombobox",
            font=("Segoe UI", 11),
            padding=(8, 6),
        )
        style.configure(
            "Wizard.Horizontal.TProgressbar",
            background=ACCENT_COLOR,
            troughcolor=ACCENT_LIGHT_COLOR,
        )

    def _create_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(
            self,
            background=ACCENT_COLOR,
            padx=24,
            pady=16,
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
        )
        header.columnconfigure(0, weight=1)

        self.page_title_label = tk.Label(
            header,
            background=ACCENT_COLOR,
            foreground="white",
            font=("Segoe UI", 18, "bold"),
        )
        self.page_title_label.grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.page_subtitle_label = tk.Label(
            header,
            background=ACCENT_COLOR,
            foreground="#DCEAF7",
            font=("Segoe UI", 10),
            wraplength=700,
        )
        self.page_subtitle_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(6, 0),
        )

        step_bar = tk.Frame(
            header,
            background=ACCENT_COLOR,
        )
        step_bar.grid(
            row=2,
            column=0,
            sticky="w",
            pady=(14, 0),
        )
        self.step_labels: list[tk.Label] = []

        for step_index, step_name in enumerate(
            STEP_NAMES
        ):
            step_label = tk.Label(
                step_bar,
                text=f"{step_index + 1}  {step_name}",
                background=ACCENT_MID_COLOR,
                foreground="white",
                font=("Segoe UI", 9, "bold"),
                padx=12,
                pady=5,
            )
            step_label.grid(
                row=0,
                column=step_index,
                padx=(
                    0,
                    (
                        8
                        if step_index < len(STEP_NAMES) - 1
                        else 0
                    ),
                ),
            )
            self.step_labels.append(step_label)

        self.content = ttk.Frame(
            self,
            padding=(24, 12, 24, 16),
        )
        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
        )
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.pages = [
            self._create_project_page(),
            self._create_access_page(),
            self._create_email_page(),
            self._create_database_page(),
            self._create_review_page(),
        ]

        footer = ttk.Frame(
            self,
            padding=(24, 12, 24, 20),
        )
        footer.grid(
            row=2,
            column=0,
            sticky="ew",
        )
        footer.columnconfigure(1, weight=1)

        self.progress = ttk.Progressbar(
            footer,
            mode="determinate",
            maximum=len(STEP_NAMES),
            value=1,
            length=150,
            style="Wizard.Horizontal.TProgressbar",
        )
        self.progress.grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.status_label = ttk.Label(
            footer,
            textvariable=self.status_var,
            style="Status.TLabel",
        )
        self.status_label.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(12, 12),
        )

        self.back_button = ttk.Button(
            footer,
            text="< Back",
            command=self.back,
        )
        self.back_button.grid(
            row=0,
            column=2,
            padx=(0, 8),
        )
        self.next_button = ttk.Button(
            footer,
            text="Next >",
            command=self.next,
            style="Accent.TButton",
        )
        self.next_button.grid(
            row=0,
            column=3,
            padx=(0, 8),
        )
        self.cancel_button = ttk.Button(
            footer,
            text="Cancel",
            command=self.cancel,
        )
        self.cancel_button.grid(
            row=0,
            column=4,
        )

    def _new_page(self) -> ttk.Frame:
        page = ttk.Frame(self.content)
        page.columnconfigure(1, weight=1)
        return page

    def _create_project_page(self) -> ttk.Frame:
        page = self._new_page()

        ttk.Label(
            page,
            text="Application name",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 14),
        )
        application_name_entry = ttk.Entry(
            page,
            textvariable=self.application_name_var,
            style="Wizard.TEntry",
        )
        application_name_entry.grid(
            row=0,
            column=1,
            columnspan=2,
            sticky="ew",
            pady=(0, 14),
        )

        ttk.Label(
            page,
            text="Project folder",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 14),
        )
        destination_entry = ttk.Entry(
            page,
            textvariable=self.destination_var,
            style="Wizard.TEntry",
        )
        destination_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(0, 14),
        )
        ttk.Button(
            page,
            text="Browse...",
            command=self.browse_destination,
        ).grid(
            row=1,
            column=2,
            padx=(10, 0),
            pady=(0, 14),
        )

        ttk.Label(
            page,
            text=(
                "Select an empty folder or enter a new folder. "
                "Existing files are never overwritten."
            ),
            wraplength=650,
            style="WizardSubtitle.TLabel",
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
        )

        page.initial_focus = application_name_entry
        return page

    def _create_access_page(self) -> ttk.Frame:
        page = self._new_page()

        mode_frame = ttk.Frame(page)
        mode_frame.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 18),
        )

        ttk.Radiobutton(
            mode_frame,
            text="Local only",
            value="local",
            variable=self.access_mode_var,
            command=self.update_access_mode,
        ).grid(
            row=0,
            column=0,
            padx=(0, 28),
        )
        ttk.Radiobutton(
            mode_frame,
            text="Public HTTPS URL (tunnel or domain)",
            value="public",
            variable=self.access_mode_var,
            command=self.update_access_mode,
        ).grid(
            row=0,
            column=1,
        )

        self.access_configuration_container = (
            ttk.Frame(page)
        )
        self.access_configuration_container.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
        )
        self.access_configuration_container.columnconfigure(
            0,
            weight=1,
        )

        self.local_access_frame = ttk.Frame(
            self.access_configuration_container
        )
        ttk.Label(
            self.local_access_frame,
            text=(
                "The application will use "
                f"{DEFAULT_PUBLIC_BASE_URL}. Choose this "
                "when it will be opened only on this computer."
            ),
            wraplength=780,
            style="WizardSubtitle.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.public_access_frame = ttk.Frame(
            self.access_configuration_container
        )
        self.public_access_frame.columnconfigure(
            1,
            weight=1,
        )
        ttk.Label(
            self.public_access_frame,
            text="Application URL",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 14),
            pady=(0, 14),
        )
        self.public_base_url_entry = ttk.Entry(
            self.public_access_frame,
            textvariable=self.public_base_url_var,
            style="Wizard.TEntry",
        )
        self.public_base_url_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=(0, 14),
        )
        ttk.Label(
            self.public_access_frame,
            text=(
                "Paste the complete HTTPS address supplied by "
                "Cloudflare Tunnel, for example "
                "https://example.trycloudflare.com. Do not add "
                "a path, query, or trailing page name. A Quick "
                "Tunnel address works only while that tunnel "
                "is running."
            ),
            wraplength=780,
            style="WizardSubtitle.TLabel",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.update_access_mode()
        return page

    def _create_email_page(self) -> ttk.Frame:
        page = self._new_page()

        mode_frame = ttk.Frame(page)
        mode_frame.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 16),
        )

        for column, (label, value) in enumerate(
            (
                ("Console", "console"),
                ("Gmail", "gmail"),
                ("Custom SMTP", "smtp"),
            )
        ):
            ttk.Radiobutton(
                mode_frame,
                text=label,
                value=value,
                variable=self.email_mode_var,
                command=self.update_email_mode,
            ).grid(
                row=0,
                column=column,
                padx=(0, 22),
            )

        self.email_configuration_container = (
            ttk.Frame(page)
        )
        self.email_configuration_container.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
        )
        self.email_configuration_container.columnconfigure(
            1,
            weight=1,
        )

        self.console_email_frame = ttk.Frame(
            self.email_configuration_container
        )
        ttk.Label(
            self.console_email_frame,
            text=(
                "Email messages will be written to the "
                "application console. No SMTP connection "
                "will be configured."
            ),
            wraplength=650,
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.gmail_email_frame = ttk.Frame(
            self.email_configuration_container
        )
        self.gmail_email_frame.columnconfigure(1, weight=1)

        gmail_guidance = tk.Frame(
            self.gmail_email_frame,
            background=ACCENT_LIGHT_COLOR,
            padx=14,
            pady=12,
        )
        gmail_guidance.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 16),
        )
        gmail_guidance.columnconfigure(0, weight=1)
        tk.Label(
            gmail_guidance,
            text=(
                "Use a Google App Password — never your "
                "normal Gmail password."
            ),
            background=ACCENT_LIGHT_COLOR,
            foreground=ACCENT_COLOR,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
        )
        tk.Label(
            gmail_guidance,
            text=(
                "1. Enable 2-Step Verification in your Google "
                "Account.  2. Create a 16-character App "
                "Password for this application.  3. Paste it "
                "below. Spaces are removed automatically."
            ),
            background=ACCENT_LIGHT_COLOR,
            foreground=TEXT_COLOR,
            font=("Segoe UI", 10),
            justify="left",
            wraplength=780,
            anchor="w",
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(6, 0),
        )
        self._add_labeled_entry(
            self.gmail_email_frame,
            1,
            "Gmail address",
            self.gmail_address_var,
        )
        self.gmail_password_entry = (
            self._add_labeled_entry(
                self.gmail_email_frame,
                2,
                "Google App Password",
                self.gmail_app_password_var,
                show="*",
            )
        )
        ttk.Checkbutton(
            self.gmail_email_frame,
            text="Show password",
            variable=self.show_email_passwords_var,
            command=self.update_password_visibility,
        ).grid(
            row=3,
            column=1,
            sticky="w",
            pady=(0, 10),
        )
        ttk.Button(
            self.gmail_email_frame,
            text="Open Google App Passwords",
            command=self.open_google_app_passwords,
        ).grid(
            row=4,
            column=1,
            sticky="w",
        )

        self.smtp_email_frame = ttk.Frame(
            self.email_configuration_container
        )
        self.smtp_email_frame.columnconfigure(1, weight=1)
        self._add_labeled_entry(
            self.smtp_email_frame,
            0,
            "SMTP host",
            self.smtp_host_var,
        )
        self._add_labeled_entry(
            self.smtp_email_frame,
            1,
            "SMTP port",
            self.smtp_port_var,
        )
        ttk.Label(
            self.smtp_email_frame,
            text="Connection security",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 10),
        )
        ttk.Combobox(
            self.smtp_email_frame,
            textvariable=self.smtp_security_var,
            values=("starttls", "ssl", "none"),
            state="readonly",
            style="Wizard.TCombobox",
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            pady=(0, 10),
        )
        self._add_labeled_entry(
            self.smtp_email_frame,
            3,
            "Username (optional)",
            self.smtp_username_var,
        )
        self.smtp_password_entry = (
            self._add_labeled_entry(
                self.smtp_email_frame,
                4,
                "Password (optional)",
                self.smtp_password_var,
                show="*",
            )
        )
        self._add_labeled_entry(
            self.smtp_email_frame,
            5,
            "Sender email",
            self.smtp_sender_email_var,
        )
        self._add_labeled_entry(
            self.smtp_email_frame,
            6,
            "Sender name (optional)",
            self.smtp_sender_name_var,
        )
        ttk.Checkbutton(
            self.smtp_email_frame,
            text="Show password",
            variable=self.show_email_passwords_var,
            command=self.update_password_visibility,
        ).grid(
            row=7,
            column=1,
            sticky="w",
        )

        self.update_email_mode()
        return page

    def _create_database_page(self) -> ttk.Frame:
        page = self._new_page()

        ttk.Label(
            page,
            text="Database provider",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 14),
        )
        provider_combobox = ttk.Combobox(
            page,
            textvariable=self.database_provider_var,
            values=tuple(
                self.database_display_to_id.keys()
            ),
            state="readonly",
            style="Wizard.TCombobox",
        )
        provider_combobox.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=(0, 14),
        )
        provider_combobox.bind(
            "<<ComboboxSelected>>",
            self.update_database_provider,
        )

        ttk.Label(
            page,
            text="SQLAlchemy URL",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 10),
        )
        self.database_url_entry = ttk.Entry(
            page,
            textvariable=self.database_url_var,
            show="*",
            style="Wizard.TEntry",
        )
        self.database_url_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(0, 10),
        )
        ttk.Checkbutton(
            page,
            text="Show URL",
            variable=self.show_database_url_var,
            command=self.update_database_url_visibility,
        ).grid(
            row=2,
            column=1,
            sticky="w",
            pady=(0, 14),
        )

        ttk.Label(
            page,
            text="Example",
        ).grid(
            row=3,
            column=0,
            sticky="nw",
            padx=(0, 12),
        )
        ttk.Label(
            page,
            textvariable=self.database_example_var,
            wraplength=560,
            style="WizardSubtitle.TLabel",
        ).grid(
            row=3,
            column=1,
            sticky="w",
        )

        self.update_database_provider()
        return page

    def _create_review_page(self) -> ttk.Frame:
        page = self._new_page()

        self.review_text = tk.Text(
            page,
            height=18,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            background=SURFACE_COLOR,
            foreground=TEXT_COLOR,
            padx=8,
            pady=8,
        )
        self.review_text.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
        )
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=1)
        self.review_text.configure(state="disabled")

        return page

    def _add_labeled_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        show: str = "",
    ) -> ttk.Entry:
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 10),
        )
        entry = ttk.Entry(
            parent,
            textvariable=variable,
            show=show,
            style="Wizard.TEntry",
        )
        entry.grid(
            row=row,
            column=1,
            sticky="ew",
            pady=(0, 10),
        )
        return entry

    def browse_destination(self) -> None:
        selected_directory = filedialog.askdirectory(
            parent=self,
            title="Select an empty project folder",
            mustexist=True,
        )

        if selected_directory:
            self.destination_var.set(
                selected_directory
            )

    def update_access_mode(self) -> None:
        for frame in (
            self.local_access_frame,
            self.public_access_frame,
        ):
            frame.grid_forget()

        if self.access_mode_var.get() == "public":
            selected_frame = self.public_access_frame
            self.public_base_url_entry.focus_set()
        else:
            selected_frame = self.local_access_frame

        selected_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    def open_google_app_passwords(self) -> None:
        if not webbrowser.open_new_tab(
            GOOGLE_APP_PASSWORDS_URL
        ):
            self.show_error(
                "The Google App Passwords page could not be "
                "opened automatically. Open this address in "
                f"your browser:\n\n{GOOGLE_APP_PASSWORDS_URL}"
            )

    def update_email_mode(self) -> None:
        for frame in (
            self.console_email_frame,
            self.gmail_email_frame,
            self.smtp_email_frame,
        ):
            frame.grid_forget()

        selected_frame = {
            "console": self.console_email_frame,
            "gmail": self.gmail_email_frame,
            "smtp": self.smtp_email_frame,
        }.get(
            self.email_mode_var.get(),
            self.console_email_frame,
        )
        selected_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    def update_password_visibility(self) -> None:
        show_value = (
            ""
            if self.show_email_passwords_var.get()
            else "*"
        )
        self.gmail_password_entry.configure(
            show=show_value
        )
        self.smtp_password_entry.configure(
            show=show_value
        )

    def update_database_url_visibility(self) -> None:
        show_value = (
            ""
            if self.show_database_url_var.get()
            else "*"
        )
        self.database_url_entry.configure(
            show=show_value
        )

    def update_database_provider(
        self,
        _event: object | None = None,
    ) -> None:
        display_name = self.database_provider_var.get()
        provider_id = self.database_display_to_id[
            display_name
        ]
        provider_profile = (
            get_database_provider_profile(
                provider_id
            )
        )

        if provider_id == DatabaseProviderId.SQLITE:
            requirement = (
                "Optional for SQLite. Leave empty to use "
                "a project-specific local database."
            )
        else:
            requirement = (
                "Required. The external database server "
                "must already exist."
            )

        self.database_example_var.set(
            f"{requirement}\n"
            f"{provider_profile.database_url_example}"
        )

    def collect_form_data(self) -> DeveloperSetupFormData:
        database_display_name = (
            self.database_provider_var.get()
        )

        return DeveloperSetupFormData(
            destination=self.destination_var.get(),
            application_name=(
                self.application_name_var.get()
            ),
            access_mode=self.access_mode_var.get(),
            public_base_url=(
                self.public_base_url_var.get()
            ),
            email_mode=self.email_mode_var.get(),
            gmail_address=self.gmail_address_var.get(),
            gmail_app_password=(
                self.gmail_app_password_var.get()
            ),
            smtp_host=self.smtp_host_var.get(),
            smtp_port=self.smtp_port_var.get(),
            smtp_security=self.smtp_security_var.get(),
            smtp_username=self.smtp_username_var.get(),
            smtp_password=self.smtp_password_var.get(),
            smtp_sender_email=(
                self.smtp_sender_email_var.get()
            ),
            smtp_sender_name=(
                self.smtp_sender_name_var.get()
            ),
            database_provider=(
                self.database_display_to_id[
                    database_display_name
                ]
            ),
            database_url=self.database_url_var.get(),
        )

    def build_request(self) -> DeveloperSetupRequest:
        try:
            return build_setup_request(
                self.collect_form_data()
            )
        except ValidationError as error:
            raise ValueError(
                format_validation_error(error)
            ) from error

    def validate_project_page(self) -> bool:
        if not self.application_name_var.get().strip():
            self.show_error(
                "Application name is required."
            )
            return False

        destination_text = self.destination_var.get().strip()

        if not destination_text:
            self.show_error(
                "Project folder is required."
            )
            return False

        try:
            validate_destination_directory(
                Path(destination_text)
                .expanduser()
                .resolve()
            )
        except (OSError, RuntimeError) as error:
            self.show_error(str(error))
            return False

        return True

    def validate_email_page(self) -> bool:
        try:
            form_data = replace(
                self.collect_form_data(),
                database_provider="sqlite",
                database_url="",
            )
            build_setup_request(form_data)
        except ValidationError as error:
            self.show_error(
                format_validation_error(error)
            )
            return False
        except (TypeError, ValueError) as error:
            self.show_error(str(error))
            return False

        return True

    def validate_access_page(self) -> bool:
        try:
            form_data = replace(
                self.collect_form_data(),
                email_mode="console",
                gmail_address="",
                gmail_app_password="",
                smtp_host="",
                smtp_port="",
                smtp_security="",
                smtp_username="",
                smtp_password="",
                smtp_sender_email="",
                smtp_sender_name="",
                database_provider="sqlite",
                database_url="",
            )
            build_setup_request(form_data)
        except ValidationError as error:
            self.show_error(
                format_validation_error(error)
            )
            return False
        except (TypeError, ValueError) as error:
            self.show_error(str(error))
            return False

        return True

    def prepare_review(self) -> bool:
        try:
            request = self.build_request()
            validate_destination_directory(
                request.destination
            )
        except (
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as error:
            self.show_error(str(error))
            return False

        self.validated_request = request
        review_text = "\n\n".join(
            line
            for line in create_review_lines(request)
            if line
        )
        self.review_text.configure(state="normal")
        self.review_text.delete("1.0", tk.END)
        self.review_text.insert("1.0", review_text)
        self.review_text.configure(state="disabled")

        return True

    def show_page(self, page_index: int) -> None:
        for page in self.pages:
            page.grid_forget()

        self.current_page_index = page_index
        page = self.pages[page_index]
        page.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        page_titles = (
            (
                "New application",
                "Choose the project identity and destination.",
            ),
            (
                "Application access",
                "Choose local access or configure the public "
                "HTTPS address used by a tunnel or domain.",
            ),
            (
                "Email configuration",
                "Choose console output, Gmail, or a custom "
                "SMTP server.",
            ),
            (
                "Database configuration",
                "Choose the SQL provider and its connection "
                "URL.",
            ),
            (
                "Review and create",
                "Confirm the configuration before creating "
                "the project.",
            ),
        )
        title, subtitle = page_titles[page_index]
        self.page_title_label.configure(text=title)
        self.page_subtitle_label.configure(
            text=subtitle
        )
        self.back_button.configure(
            state=(
                "disabled"
                if page_index == 0
                else "normal"
            )
        )
        self.next_button.configure(
            text=(
                "Create project"
                if page_index == len(self.pages) - 1
                else "Next >"
            )
        )
        self.status_var.set(
            f"Step {page_index + 1} of {len(self.pages)}"
        )
        self.update_progress_display()

        initial_focus = getattr(
            page,
            "initial_focus",
            None,
        )
        if initial_focus is not None:
            initial_focus.focus_set()

    def update_progress_display(self) -> None:
        self.progress.configure(
            mode="determinate",
            maximum=len(STEP_NAMES),
            value=self.current_page_index + 1,
        )

        step_states = create_step_states(
            self.current_page_index
        )

        for step_index, (
            step_label,
            step_state,
        ) in enumerate(
            zip(
                self.step_labels,
                step_states,
                strict=True,
            )
        ):
            step_name = STEP_NAMES[step_index]

            if step_state == "completed":
                step_label.configure(
                    text=f"✓  {step_name}",
                    background=SUCCESS_COLOR,
                    foreground="white",
                )
            elif step_state == "current":
                step_label.configure(
                    text=f"{step_index + 1}  {step_name}",
                    background="white",
                    foreground=ACCENT_COLOR,
                )
            else:
                step_label.configure(
                    text=f"{step_index + 1}  {step_name}",
                    background=ACCENT_MID_COLOR,
                    foreground="white",
                )

    def next(self) -> None:
        if self.is_busy:
            return

        if self.current_page_index == 0:
            if not self.validate_project_page():
                return
        elif self.current_page_index == 1:
            if not self.validate_access_page():
                return
        elif self.current_page_index == 2:
            if not self.validate_email_page():
                return
        elif self.current_page_index == 3:
            if not self.prepare_review():
                return
        else:
            self.create_project()
            return

        self.show_page(
            self.current_page_index + 1
        )

    def back(self) -> None:
        if self.is_busy or self.current_page_index == 0:
            return

        self.show_page(
            self.current_page_index - 1
        )

    def create_project(self) -> None:
        if not self.prepare_review():
            return

        request = self.validated_request

        if request is None:
            self.show_error(
                "The setup request is unavailable."
            )
            return

        self.set_busy(True)
        self.status_var.set("Creating application project...")

        worker = Thread(
            target=self._create_project_worker,
            args=(request,),
            daemon=True,
        )
        worker.start()
        self.after(100, self.poll_result)

    def _create_project_worker(
        self,
        request: DeveloperSetupRequest,
    ) -> None:
        try:
            create_application_project(request)
        except Exception as error:
            self.result_queue.put(
                (False, str(error))
            )
        else:
            self.result_queue.put(
                (True, str(request.destination))
            )

    def poll_result(self) -> None:
        try:
            succeeded, result_text = (
                self.result_queue.get_nowait()
            )
        except Empty:
            self.after(100, self.poll_result)
            return

        self.set_busy(False)

        if succeeded:
            self.status_var.set(
                "Project created successfully."
            )
            messagebox.showinfo(
                "Project created",
                "The application project was created "
                f"successfully:\n\n{result_text}",
                parent=self,
            )
            self.destroy()
        else:
            self.show_error(result_text)
            self.status_var.set("Project creation failed.")

    def set_busy(self, busy: bool) -> None:
        self.is_busy = busy
        button_state = (
            "disabled"
            if busy
            else "normal"
        )

        self.next_button.configure(
            state=button_state
        )
        self.cancel_button.configure(
            state=button_state
        )
        self.back_button.configure(
            state=(
                "disabled"
                if busy or self.current_page_index == 0
                else "normal"
            )
        )

        if busy:
            self.progress.configure(
                mode="indeterminate"
            )
            self.progress.start(10)
        else:
            self.progress.stop()
            self.update_progress_display()

    def show_error(self, message: str) -> None:
        messagebox.showerror(
            "Developer Setup",
            message,
            parent=self,
        )

    def cancel(self) -> None:
        if self.is_busy:
            return

        if messagebox.askyesno(
            "Cancel setup",
            "Close Developer Setup without creating "
            "a project?",
            parent=self,
        ):
            self.destroy()


def main() -> None:
    wizard = DeveloperSetupWizard()
    wizard.mainloop()


if __name__ == "__main__":
    main()
