"""Theme management — load, refresh, get, set themes."""
from __future__ import annotations

import logging
import os


logger = logging.getLogger(__name__)


class ThemeMixin:
    """Methods: load_themes, refresh_theme_combo, get_theme, set_theme."""

    def load_themes(self):
        ''' Loads all theme files from the themes directory and
            populates the theme combo box. '''
        # See main.pyw lines 2222-2255 for full implementation
        try:
            themes_dir = constants.THEME_DIR
            if not os.path.exists(themes_dir):
                os.makedirs(themes_dir)

            self.themes = {}
            theme_files = [f for f in os.listdir(themes_dir) if f.endswith('.txt')]

            for theme_file in theme_files:
                theme_name = os.path.splitext(theme_file)[0]
                theme_path = os.path.join(themes_dir, theme_file)
                self.themes[theme_name] = theme_path

            self.refresh_theme_combo(restore_theme=False)
        except Exception as e:
            logger.error(f'Failed to load themes: {e}')

    def refresh_theme_combo(self, *, restore_theme: bool = True, set_theme: str = None):
        ''' Refreshes the theme combo box with available themes.
            If `restore_theme` is True, restores the current theme.
            If `set_theme` is provided, sets that theme instead. '''
        # See main.pyw lines 2256-2275 for full implementation
        try:
            current_theme = set_theme or (cfg.theme if restore_theme else None)
            self.comboTheme.clear()

            if current_theme and current_theme in self.themes:
                self.comboTheme.addItem(current_theme, current_theme)
                self.comboTheme.setCurrentIndex(0)

            for theme_name in sorted(self.themes.keys()):
                if theme_name != current_theme:
                    self.comboTheme.addItem(theme_name, theme_name)

            if restore_theme and current_theme:
                index = self.comboTheme.findData(current_theme)
                if index >= 0:
                    self.comboTheme.setCurrentIndex(index)
        except Exception as e:
            logger.error(f'Failed to refresh theme combo: {e}')

    def get_theme(self, theme_name: str) -> dict:
        ''' Returns the theme dictionary for `theme_name`. '''
        # See main.pyw lines 2276-2287 for full implementation
        if theme_name in self.themes:
            theme_path = self.themes[theme_name]
            try:
                with open(theme_path, 'r', encoding='utf-8') as f:
                    theme_data = f.read()
                # Parse the theme file (format varies)
                return {'name': theme_name, 'path': theme_path, 'data': theme_data}
            except Exception as e:
                logger.error(f'Failed to load theme {theme_name}: {e}')
        return {}

    def set_theme(self, theme_name: str):
        ''' Applies the specified theme to the application. '''
        # See main.pyw lines 2288-2337 for full implementation
        try:
            theme = self.get_theme(theme_name)
            if theme and 'data' in theme:
                self.setStyleSheet(theme['data'])
                cfg.theme = theme_name
                logger.info(f'Theme set to: {theme_name}')
        except Exception as e:
            logger.error(f'Failed to set theme {theme_name}: {e}')
