import re

from bs4 import BeautifulSoup, NavigableString, Tag

# Configurações
HTML_FILE = "./pg33931-images.html"          # Coloque o nome exato do seu arquivo HTML/.xhtml aqui
OUTPUT_TEX = "poemas_extraidos.tex"
MACRO_NOTA = "pagenote"

with open(HTML_FILE, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# 1. Extrair todas as notas de rodapé do HTML para um dicionário
footnotes = {}
for fn_div in soup.find_all("div", class_="footnote"):
    # Procura o ID da nota, ex: Footnote_101
    a_tag = fn_div.find("a", id=re.compile(r"Footnote_\d+"))
    if a_tag:
        fn_num = a_tag["id"].split("_")[1]
        # Remove o link do número [101] para pegar só o texto limpo
        for label in fn_div.find_all("a", class_="pginternal"):
            label.decompose()
        # Limpa quebras de linha internas do HTML e escapa o &
        fn_text = " ".join(fn_div.get_text().split())
        fn_text = fn_text.replace("&", r"\&")
        footnotes[fn_num] = fn_text

# 2. Função recursiva para converter o conteúdo interno de um verso para LaTeX
def html_line_to_latex(element):
    latex_str = ""
    for child in element.children:
        if isinstance(child, NavigableString):
            # Remove quebras de linha do código HTML e escapa caracteres do LaTeX
            text = re.sub(r'\s+', ' ', str(child))
            text = text.replace("&", r"\&").replace("%", r"\%")
            latex_str += text
        elif isinstance(child, Tag):
            if child.name in ["i", "em"]:
                latex_str += f"\\emph{{{html_line_to_latex(child)}}}"
            elif child.name == "span" and "smcap" in child.get("class", []):
                latex_str += f"\\textsc{{{html_line_to_latex(child)}}}"
            elif child.name == "a" and "fnanchor" in child.get("class", []):
                # É uma chamada de nota de rodapé! Ex: href="#Footnote_101"
                href = child.get("href", "")
                match = re.search(r"Footnote_(\d+)", href)
                if match:
                    fn_num = match.group(1)
                    fn_content = footnotes.get(fn_num, f"TODO_NOTA_{fn_num}")
                    latex_str += f"\\{MACRO_NOTA}{{{fn_content}}}"
            else:
                # Outras tags (como <a id="FNanchor_101"> vazio), apenas processa o interior
                latex_str += html_line_to_latex(child)
    return latex_str

# 3. Mapear classes de indentação (i0, i2, i4...) para comandos do memoir
def get_indent_prefix(classes):
    for c in classes:
        match = re.match(r"i(\d+)", c)
        if match:
            level = int(match.group(1))
            if level == 0:
                return ""
            elif level <= 4:
                return r"\vin "
            else:
                # Para recuos muito profundos (ex: i6, i8), aplica \vin duplo
                return r"\vin\vin "
    return ""

# 4. Extrair todos os poemas
poems_latex = []
poem_divs = soup.find_all("div", class_="poem")

for idx, poem in enumerate(poem_divs, 1):
    lines_out = [f"% === POEMA {idx} ===", r"\begin{verse}"]

    # Verifica se o poema é dividido em <div class="stanza"> ou se os spans estão diretos
    stanzas = poem.find_all("div", class_="stanza")
    if not stanzas:
        stanzas = [poem] # Trata o próprio bloco poem como uma única estrofe

    for s_idx, stanza in enumerate(stanzas):
        spans = stanza.find_all("span", class_=re.compile(r"^i\d+"))
        for l_idx, span in enumerate(spans):
            indent = get_indent_prefix(span.get("class", []))
            line_text = html_line_to_latex(span).strip()

            # O último verso da estrofe não leva \\ no final
            is_last_line_of_stanza = (l_idx == len(spans) - 1)
            linebreak = "" if is_last_line_of_stanza else r" \\"

            lines_out.append(f"{indent}{line_text}{linebreak}")

        # Se houver mais estrofes neste poema, adiciona uma linha em branco entre elas
        if s_idx < len(stanzas) - 1:
            lines_out.append("")

    lines_out.append(r"\end{verse}" + "\n")
    poems_latex.append("\n".join(lines_out))

with open(OUTPUT_TEX, "w", encoding="utf-8") as f:
    f.write("\n".join(poems_latex))

print(f"Sucesso! {len(poem_divs)} blocos de poemas foram extraídos e salvos em '{OUTPUT_TEX}'.")
