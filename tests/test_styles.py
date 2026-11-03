from common.utils import load_css


def test_print_stylesheet_hides_menu_and_buttons_when_printing():
    css = load_css("print.css")
    assert "@media print" in css
    for selector in ('[data-testid="stSidebar"]', '[data-testid="stDownloadButton"]', "iframe"):
        assert selector in css
