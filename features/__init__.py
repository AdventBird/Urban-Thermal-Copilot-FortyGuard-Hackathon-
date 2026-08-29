"""Urban Thermal Copilot feature modules.

Each module wraps the reusable business logic in the ``utc`` package and adds
Streamlit-friendly presentation helpers. The shared ``data_layer`` here decides
between live API / local cache / fixture-backed mock mode so the whole app runs
end-to-end without any API key.
"""