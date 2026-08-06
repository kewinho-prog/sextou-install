#!/usr/bin/env bash
# install.sh — o único arquivo público desta instalação.
#
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kewinho-prog/prima-install/main/install.sh)"
#
# ── Por que este arquivo existe separado
#
# O repositório da Prima é privado, e o servidor de arquivos brutos não entrega
# repositório privado sem autenticação. Então o começo da instalação mora aqui,
# num repositório público que contém APENAS este script: nenhuma skill, nenhum
# motor, nenhuma regra, nenhum caminho de máquina. Nada aqui tem valor se
# alguém copiar.
#
# ── Por que não `curl | bash`
#
# Com o cano, a entrada padrão do script É o próprio script. O login no
# repositório precisa de um terminal de verdade para você colar o código que
# aparece no navegador — e sem esse login não há como baixar um repositório
# privado. A forma com `$(...)` baixa primeiro e roda depois, com o terminal
# livre. A forma com cano simplesmente não termina.
set -uo pipefail

REPO="kewinho-prog/PrimaCore"
DESTINO="$HOME/.prima/core"

if [[ -t 1 ]]; then V=$'\033[32m'; A=$'\033[33m'; E=$'\033[31m'; D=$'\033[2m'; F=$'\033[0m'
else V=''; A=''; E=''; D=''; F=''; fi
ok()   { printf '  %s✓%s %s\n' "$V" "$F" "$1"; }
aviso(){ printf '  %s!%s %s\n' "$A" "$F" "$1"; }
falta(){ printf '\n  %s✗ %s%s\n    %spor quê:%s %s\n    %so que fazer:%s %s\n' "$E" "$1" "$F" "$D" "$F" "$2" "$D" "$F" "$3"; }

cat <<'ABERTURA'

  Prima
  Assistente operacional que roda na sua máquina, com as suas chaves.

  Isto vai:
    1. conferir o que falta (e parar, sem instalar nada à força)
    2. pedir seu login no repositório, pelo navegador
    3. baixar em ~/.prima/core
    4. mostrar tudo que mudaria — sem mudar nada
    5. você confere e confirma

ABERTURA

[[ "$(uname)" == "Darwin" ]] || { falta "isto só foi testado em macOS" "os caminhos e os agentes são de macOS" "instale à mão a partir do repositório"; exit 1; }

falhas=0
echo "  Conferindo:"

if command -v git >/dev/null 2>&1; then ok "git"
else falta "git não está instalado" "é como o repositório é baixado e atualizado" "rode: xcode-select --install"; falhas=$((falhas+1)); fi

if command -v node >/dev/null 2>&1 && [[ "$(node -v | sed 's/v//;s/\..*//')" -ge 20 ]]; then
  ok "node $(node -v)"
else
  falta "node ausente ou anterior à versão 20" "os motores e o índice de capacidades dependem dele" "rode: brew install node"
  falhas=$((falhas+1))
fi

if command -v gh >/dev/null 2>&1; then ok "cliente do repositório"
else falta "o cliente do repositório não está instalado" "é o único caminho para baixar um repositório privado" "rode: brew install gh"; falhas=$((falhas+1)); fi

if [[ -d "$HOME/.codex" ]]; then ok "agente principal"
else falta "o agente principal não está instalado" "é ele que carrega as capacidades e as regras" "instale-o e rode este comando de novo"; falhas=$((falhas+1)); fi

[[ -d "$HOME/.config/opencode" ]] && ok "agente secundário" || aviso "agente secundário ausente — opcional"

if (( falhas > 0 )); then
  printf '\n  %s pré-requisito(s) faltando. Resolva os itens acima e rode de novo.\n\n' "$falhas" >&2
  exit 1
fi

# ── Login
if ! gh auth status >/dev/null 2>&1; then
  cat <<'LOGIN'

  Falta o login. Vai abrir o navegador e mostrar um código de 8 caracteres
  aqui no terminal — é só colar lá e autorizar.

  O acesso fica guardado no chaveiro do seu computador. Depois disso, tudo
  funciona sozinho.

LOGIN
  read -r -p "  Continuar? [S/n] " r
  [[ "${r:-s}" =~ ^[SsYy]?$ ]] || { echo "  Cancelado."; exit 0; }
  gh auth login --web --git-protocol https || { falta "o login não foi concluído" "sem ele não há como baixar um repositório privado" "rode: gh auth login"; exit 1; }
fi
ok "acesso confirmado"

# ── Baixar
echo ""
if [[ -d "$DESTINO/.git" ]]; then
  echo "  Já existe uma instalação. Atualizando..."
  git -C "$DESTINO" fetch --quiet origin && git -C "$DESTINO" merge --ff-only --quiet origin/main 2>/dev/null \
    || aviso "não deu para atualizar automaticamente — veja: git -C $DESTINO status"
  ok "em $DESTINO"
else
  echo "  Baixando..."
  mkdir -p "$(dirname "$DESTINO")"
  if ! gh repo clone "$REPO" "$DESTINO" -- --quiet 2>/dev/null; then
    falta "não consegui baixar o repositório" \
      "ou o seu acesso ainda não foi liberado, ou o nome do repositório mudou" \
      "peça acesso de leitura a $REPO a quem te entregou isto"
    exit 1
  fi
  ok "baixado em $DESTINO"
fi

# ── Verificação, nunca aplicação direta
cat <<'ANTES'

  Agora vem o diagnóstico. Nada é alterado neste passo — você vai ver
  exatamente o que mudaria antes de decidir.

ANTES

bash "$DESTINO/instalador/instalar.sh"

cat <<APLICAR

  Se estiver de acordo, instale de verdade com:

      bash $DESTINO/instalador/instalar.sh --aplicar

  Depois: prima ola

APLICAR
