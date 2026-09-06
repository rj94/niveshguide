from bs4 import BeautifulSoup

from ingestion.screener_in.numbers import normalize_key, parse_number
from ingestion.screener_in.parse import parse_company_html, parse_peers_taxonomy


def test_parse_number():
    assert parse_number("14.89%") == 14.89
    assert parse_number("53,319") == 53319.0
    assert parse_number("(12)") == -12.0
    assert parse_number("-") is None


def test_normalize_key_strips_plus():
    assert normalize_key("Promoters +") == "promoters"
    assert normalize_key("FIIs +") == "fiis"


def test_parse_peers_taxonomy():
    html = """
    <section id="peers">
      <p class="sub">
        <a href="/market/IN08/" title="Broad Sector">Information Technology</a>
        <a href="/market/IN08/IN0801/" title="Sector">Information Technology</a>
        <a href="/market/x/" title="Broad Industry">IT - Software</a>
        <a href="/market/y/" title="Industry">Computers - Software &amp; Consulting</a>
      </p>
    </section>
    """
    tax = parse_peers_taxonomy(BeautifulSoup(html, "lxml"))
    assert tax["broad_sector"] == "Information Technology"
    assert tax["sector"] == "Information Technology"
    assert tax["broad_industry"] == "IT - Software"
    assert tax["industry"] == "Computers - Software & Consulting"


def test_parse_shareholding_fixture():
    html = """
    <html><body>
    <h1>Infosys Ltd</h1>
    <ul id="top-ratios">
      <li><span class="name">Stock P/E</span><span class="value">14.9</span></li>
      <li><span class="name">ROE</span><span class="value">29.5%</span></li>
    </ul>
    <section id="shareholding">
      <table>
        <tr><th></th><th>Mar 2026</th><th>Jun 2026</th></tr>
        <tr><td>Promoters +</td><td>14.00%</td><td>13.82%</td></tr>
        <tr><td>FIIs +</td><td>28.45%</td><td>27.09%</td></tr>
        <tr><td>DIIs +</td><td>40.00%</td><td>42.78%</td></tr>
        <tr><td>Public +</td><td>16.00%</td><td>15.88%</td></tr>
      </table>
    </section>
    <section id="profit-loss">
      <table>
        <tr><th></th><th>Mar 2025</th><th>Mar 2026</th></tr>
        <tr><td>Sales +</td><td>1,00,000</td><td>1,10,000</td></tr>
        <tr><td>Net Profit +</td><td>10,000</td><td>12,000</td></tr>
      </table>
    </section>
    </body></html>
    """
    parsed = parse_company_html("INFY", html, source_url="https://www.screener.in/company/INFY/")
    assert parsed.status == "ok"
    assert parsed.ratios.get("pe_num") == 14.9
    assert parsed.shareholding_latest.get("promoter_pct") == 13.82
    assert parsed.shareholding_latest.get("fii_pct") == 27.09
    assert parsed.shareholding_latest.get("dii_pct") == 42.78
    assert any(row.section == "profit-loss" and row.metric.startswith("Sales") for row in parsed.long_rows)
