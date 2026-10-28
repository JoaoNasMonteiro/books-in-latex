import re

# Configurações
INPUT_FILE = "main.tex"
OUTPUT_FILE = "main_limpo.tex"
MACRO_NAME = "pagenote"  # ou "footnote"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Padrão das DEFINIÇÕES das notas (Footnote_X)
def_header_pattern = re.compile(
    r"\\protect\\hypertarget\{[^}]*?Footnote_(\d+)\}\{\}\{\}\s*\\protect\\hyperlink\{[^}]*?FNanchor_\1\}\{\{+\[\}\1\{\]\}+\}\s*"
)

# 2. Padrão das CHAMADAS no corpo do texto (FNanchor_X)
anchor_pattern_flex = re.compile(
    r"\\protect\\hypertarget\{[^}]*?FNanchor_(\d+)\}\{\}\{\}\s*\\protect\\hyperlink\{[^}]*?Footnote_\1\}\{\{+\[\}\1\{\]\}+\}"
)

# Marcadores de fim de seção para saber onde uma nota multi-parágrafo termina
end_boundary_pattern = re.compile(
    r"\n\s*(?=\\hypertarget|\\section|\\subsection|\\chapter|\\part|\\newpage|\\end\{otherlanguage\}|\{Fairies and Ogres\.\})"
)

# --- FASE 0: Mapear quais âncoras realmente existem no texto ---
existing_anchors = set(m.group(1) for m in anchor_pattern_flex.finditer(content))

# --- FASE 1: Extrair definições e verificar se têm âncora correspondente ---
footnotes = {}
matches = list(def_header_pattern.finditer(content))
replacements_in_defs = []  # Guarda (start, end, replacement_string)

orphan_defs_count = 0

for i, match in enumerate(matches):
    fn_num = match.group(1)
    start_pos = match.end()

    next_def_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
    chunk = content[start_pos:next_def_pos]
    boundary_match = end_boundary_pattern.search(chunk)

    if boundary_match:
        end_pos = start_pos + boundary_match.start()
    else:
        if i + 1 < len(matches) and (next_def_pos - start_pos) < 1500:
            end_pos = next_def_pos
        else:
            double_newline = chunk.find("\n\n")
            end_pos = (
                start_pos + double_newline if double_newline != -1 else next_def_pos
            )

    fn_text = content[start_pos:end_pos].strip()
    footnotes[fn_num] = fn_text

    # Verifica se esta definição tem onde ser inserida no texto
    if fn_num in existing_anchors:
        # Tem âncora! Então apagamos a definição daqui (substituímos por vazio)
        replacements_in_defs.append((match.start(), end_pos, ""))
    else:
        # MISMATCH TIPO 1: Definição existe, mas não há chamada no texto!
        orphan_defs_count += 1
        warning_block = (
            f"\n\n% ===================================================================\n"
            f"% TODO_NOTA_MISMATCH [DEFINIÇÃO ÓRFÃ - NOTA {fn_num}]:\n"
            f"% O texto abaixo pertence à nota [{fn_num}], mas não há chamada (FNanchor_{fn_num}) no texto.\n"
            f"% Verifique no original onde encaixar este \\{MACRO_NAME}{{...}}:\n"
            f"\\textbf{{[NOTA ÓRFÃ {fn_num}:}} {fn_text}\\textbf{{]}}\n"
            f"% ===================================================================\n\n"
        )
        replacements_in_defs.append((match.start(), end_pos, warning_block))

# Aplica as remoções/avisos nas definições de trás para frente
content_cleaned = content
for start, end, rep_str in reversed(replacements_in_defs):
    content_cleaned = content_cleaned[:start] + rep_str + content_cleaned[end:]

# --- FASE 2: Substituir as âncoras no texto ou marcar Âncoras Órfãs ---
replaced_count = 0
orphan_anchors_count = 0


def replace_anchor(match):
    global replaced_count, orphan_anchors_count
    fn_num = match.group(1)
    if fn_num in footnotes:
        replaced_count += 1
        return f"\\{MACRO_NAME}{{{footnotes[fn_num]}}}"
    else:
        # MISMATCH TIPO 2: Chamada existe no texto, mas a definição não foi achada!
        orphan_anchors_count += 1
        return (
            f"\\textbf{{[TODO\\_NOTA\\_MISMATCH: ÂNCORA {fn_num} SEM TEXTO]}}"
            f"% <-- Busque por Footnote_{fn_num} no original\n"
        )


final_content = anchor_pattern_flex.sub(replace_anchor, content_cleaned)

# Limpa excesso de quebras de linha
final_content = re.sub(r"\n{3,}", "\n\n", final_content)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(final_content)

print(f"--- RELATÓRIO DE EXECUÇÃO ---")
print(f"Notas convertidas com perfeição: {replaced_count}")
print(f"Definições órfãs (sem âncora no texto): {orphan_defs_count}")
print(f"Âncoras órfãs (sem texto de definição): {orphan_anchors_count}")
print(f"Para encontrar os problemas no Vim, busque por: /TODO_NOTA_MISMATCH")
