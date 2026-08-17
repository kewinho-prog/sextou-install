#!/usr/bin/env bash
# install.sh — o único arquivo público desta instalação.
#
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kewinho-prog/sextou-install/main/install.sh)"
#
# ── Por que este arquivo existe separado
#
# O repositório do SextouCore é privado, e o servidor de arquivos brutos não entrega
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

REPO="kewinho-prog/SextouCore"
# Destino configurável: permite provar a instalação inteira num diretório
# descartável antes de mandá-la para a máquina de alguém. Sem isso, o único
# jeito de testar este script é rodá-lo de verdade — e "testei mentalmente"
# não é teste.
#
# SEXTOU_CORE é o nome de hoje; PRIMA_CORE continua sendo aceito porque quem
# exportou a variável antiga não tem como saber que o produto mudou de nome.
DESTINO="${SEXTOU_CORE:-${PRIMA_CORE:-$HOME/.sextou/core}}"
ANTIGO="$HOME/.prima/core"

# Quem instalou como Prima tem um clone git em ~/.prima/core. Se este script
# simplesmente apontasse para o caminho novo, ele CLONARIA DE NOVO — duas
# cópias na máquina, e a antiga ficando velha em silêncio. Então o clone
# antigo é movido, uma vez, antes de qualquer decisão de baixar.
if [[ ! -d "$DESTINO/.git" && -d "$ANTIGO/.git" ]]; then
  mkdir -p "$(dirname "$DESTINO")"
  if mv "$ANTIGO" "$DESTINO" 2>/dev/null; then
    printf '  o programa mudou de nome: %s agora fica em %s\n' "$ANTIGO" "$DESTINO"
    # O endereço do repositório também mudou. O GitHub redireciona, mas deixar
    # o endereço velho gravado é dívida que aparece no dia em que ele parar.
    git -C "$DESTINO" remote set-url origin "https://github.com/$REPO.git" 2>/dev/null || true
    rmdir "$(dirname "$ANTIGO")" 2>/dev/null || true
  fi
fi

if [[ -t 1 ]]; then V=$'\033[32m'; A=$'\033[33m'; E=$'\033[31m'; D=$'\033[2m'; F=$'\033[0m'
else V=''; A=''; E=''; D=''; F=''; fi
ok()   { printf '  %s✓%s %s\n' "$V" "$F" "$1"; }
aviso(){ printf '  %s!%s %s\n' "$A" "$F" "$1"; }
falta(){ printf '\n  %s✗ %s%s\n    %spor quê:%s %s\n    %so que fazer:%s %s\n' "$E" "$1" "$F" "$D" "$F" "$2" "$D" "$F" "$3"; }

cat <<'ABERTURA'

  Sextou
  Assistente operacional que roda na sua máquina, com as suas chaves.

  Isto vai:
    1. conferir o que falta (e parar, sem instalar nada à força)
    2. pedir seu login no repositório, pelo navegador
    3. baixar em ~/.sextou/core
    4. mostrar tudo que mudaria — sem mudar nada
    5. você confere e confirma

ABERTURA

# macOS e Linux rodam isto num shell de verdade. Windows não tem shell POSIX
# nativo — mas o Git for Windows traz um (MSYS2/Git Bash), e é dentro dele que
# este script deve ser colado. `uname` ali responde MINGW64_NT-* (ou MSYS_NT-*,
# CYGWIN_NT-*, dependendo da instalação), nunca "Windows" — por isso o teste é
# por prefixo, não por igualdade.
SO="$(uname)"
case "$SO" in
  Darwin|Linux) ;;
  MINGW*|MSYS*|CYGWIN*) ;;
  *) falta "sistema não suportado: $SO" "os caminhos e os agentes são pensados para macOS, Linux e Windows" \
       "no Windows, instale o Git for Windows (git-scm.com) e rode este comando de novo dentro do Git Bash"
     exit 1 ;;
esac

# Sem Homebrew (todo Windows, e Linux que não o usa), a sugestão de instalação
# não pode ser um `brew install` que não existe nessa máquina — isso trocaria
# um erro claro por um comando que falha calado.
TEM_BREW=0; command -v brew >/dev/null 2>&1 && TEM_BREW=1

falhas=0
echo "  Conferindo:"

if command -v git >/dev/null 2>&1; then ok "git"
else
  if (( TEM_BREW == 1 )); then
    falta "git não está instalado" "é como o repositório é baixado e atualizado" "rode: xcode-select --install"
  else
    falta "git não está instalado" "é como o repositório é baixado e atualizado" "baixe em https://git-scm.com/downloads (no Windows, isso já traz o Git Bash)"
  fi
  falhas=$((falhas+1))
fi

if command -v node >/dev/null 2>&1 && [[ "$(node -v | sed 's/v//;s/\..*//')" -ge 20 ]]; then
  ok "node $(node -v)"
else
  if (( TEM_BREW == 1 )); then
    falta "node ausente ou anterior à versão 20" "os motores e o índice de capacidades dependem dele" "rode: brew install node"
  else
    falta "node ausente ou anterior à versão 20" "os motores e o índice de capacidades dependem dele" "baixe em https://nodejs.org/ (LTS, versão 20 ou mais nova)"
  fi
  falhas=$((falhas+1))
fi

if command -v gh >/dev/null 2>&1; then ok "cliente do repositório"
else
  if (( TEM_BREW == 1 )); then
    falta "o cliente do repositório não está instalado" "é o único caminho para baixar um repositório privado" "rode: brew install gh"
  else
    falta "o cliente do repositório não está instalado" "é o único caminho para baixar um repositório privado" "baixe em https://cli.github.com/ (ou: winget install --id GitHub.cli)"
  fi
  falhas=$((falhas+1))
fi

if [[ -d "$HOME/.claude" ]]; then ok "agente principal"
else falta "o agente principal não está instalado" "é ele que carrega as capacidades e as regras" \
  "instale o Claude Code (https://claude.com/product/claude-code) e rode este comando de novo"; falhas=$((falhas+1)); fi

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

# Ensina o git a usar o acesso guardado, por HTTPS. Sem isto, quem já tinha o
# cliente configurado para SSH tenta clonar por SSH — e falha com "permissão
# negada (publickey)", que parece falta de acesso ao repositório quando é só
# falta de uma chave SSH que ninguém pediu.
gh auth setup-git >/dev/null 2>&1 || true

# ── Baixar
echo ""
if [[ -d "$DESTINO/.git" ]]; then
  echo "  Já existe uma instalação. Atualizando..."
  git -C "$DESTINO" fetch --quiet origin 2>/dev/null && git -C "$DESTINO" merge --ff-only --quiet origin/main 2>/dev/null \
    || aviso "não deu para atualizar automaticamente — veja: git -C $DESTINO status"
  ok "em $DESTINO"
else
  echo "  Baixando..."
  mkdir -p "$(dirname "$DESTINO")"
  # git clone por HTTPS explícito, e não `gh repo clone`: aquele respeita a
  # preferência de protocolo já configurada na máquina, que pode ser SSH.
  if ! git clone --quiet "https://github.com/$REPO.git" "$DESTINO" 2>/dev/null; then
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

  Depois: sextou ola

APLICAR
