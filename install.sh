#!/usr/bin/env bash
# install.sh — bootstrap público do Sextou.
#
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kewinho-prog/sextou-install/main/install.sh)" -- \
#     [--provedor codex|claude|gemini|opencode|local|codex-local]
#
# Este arquivo é o único público desta instalação: o repositório do
# SextouCore é privado, e por isso o começo mora aqui.
#
# Este script SÓ prepara o terreno — confere pré-requisitos, autentica,
# baixa (ou reconhece) o SextouCore e delega ao instalador adaptativo do
# próprio Core, que ainda é CANDIDATO, não publicado como caminho padrão.
# Se o instalador adaptativo não existir no que foi baixado, este script
# recusa com um código estável — nunca cai para um caminho legado.
#
# Isto não é prova de que o produto inteiro já foi instalado: quem faz o
# diagnóstico de verdade (provedor, credenciais, capacidades) é o
# instalador adaptativo, dentro do Core.
set -uo pipefail

REPO="kewinho-prog/SextouCore"
# SEXTOU_CORE é o nome de hoje; PRIMA_CORE continua aceito por quem exportou
# a variável antiga e não tem como saber que o produto mudou de nome.
DESTINO="${SEXTOU_CORE:-${PRIMA_CORE:-$HOME/.sextou/core}}"

if [[ -t 1 ]]; then V=$'\033[32m'; A=$'\033[33m'; E=$'\033[31m'; D=$'\033[2m'; F=$'\033[0m'
else V=''; A=''; E=''; D=''; F=''; fi
ok()   { printf '  %s✓%s %s\n' "$V" "$F" "$1"; }
aviso(){ printf '  %s!%s %s\n' "$A" "$F" "$1"; }
falta(){ printf '\n  %s✗ %s%s\n    %spor quê:%s %s\n    %so que fazer:%s %s\n' "$E" "$1" "$F" "$D" "$F" "$2" "$D" "$F" "$3" >&2; }

# ── Argumentos ─────────────────────────────────────────────────────────
# Só --provedor é aceito aqui. Desconhecido,
# duplicado ou sem valor: falha ANTES de qualquer escrita, login ou
# download. As flags --adaptativo e --aplicar não são aceitas aqui: o
# bootstrap já escolhe o caminho adaptativo, e aplicar exige
# uma segunda invocação explícita, depois de conferir a prévia.
PROVEDOR=""
VISTOS=" "
while [[ $# -gt 0 ]]; do
  flag="$1"
  case "$flag" in --provedor) ;; *) falta "ARGUMENTO_INVALIDO" "opção não reconhecida" "use apenas --provedor; nome e comando serão definidos pela primeira conversa com a IA"; exit 2;; esac
  case "$VISTOS" in *" $flag "*) falta "ARGUMENTO_INVALIDO" "opção repetida" "informe cada opção uma vez"; exit 2;; esac
  if [[ $# -lt 2 || -z "${2//[[:space:]]/}" || "$2" == --* ]]; then
    falta "ARGUMENTO_INVALIDO" "valor ausente" "informe um valor após cada opção"; exit 2
  fi
  VISTOS+="$flag "
  case "$flag" in
    --provedor)
      case "$2" in codex|claude|gemini|opencode|local|codex-local) PROVEDOR="$2" ;; *) falta "ARGUMENTO_INVALIDO" "provedor desconhecido" "escolha codex, claude, gemini, opencode, local ou codex-local"; exit 2;; esac ;;
  esac
  shift 2
done
[[ "$DESTINO" == /* ]] || { falta "DESTINO_INVALIDO" "caminho deve ser absoluto" "use um caminho completo em SEXTOU_CORE"; exit 2; }

cat <<'ABERTURA'

  Sextou — bootstrap (instalador adaptativo: candidato, ainda não publicado)

  Isto vai:
    1. conferir o que falta (e parar, sem instalar nada à força)
    2. pedir seu login no repositório, só se ainda faltar, e só com
       confirmação sua
    3. conferir o acesso ao repositório, separado do login
    4. reconhecer um checkout já existente sem mexer nele, ou baixar um
       novo em ~/.sextou/core
    5. delegar o diagnóstico e a prévia ao instalador adaptativo do Core
       — nada é aplicado neste passo

  Isto NÃO é a instalação inteira, e não instala nada sozinho.

ABERTURA

SO="$(uname)"
case "$SO" in
  Darwin|Linux) ;;
  MINGW*|MSYS*|CYGWIN*) ;;
  *) falta "sistema não suportado: $SO" "os caminhos são pensados para macOS, Linux e Windows (Git Bash)" \
       "no Windows, instale o Git for Windows (git-scm.com) e rode este comando de novo dentro do Git Bash"
     exit 1 ;;
esac

TEM_BREW=0; command -v brew >/dev/null 2>&1 && TEM_BREW=1

falhas=0
echo "  Conferindo:"

if command -v git >/dev/null 2>&1; then ok "git"
else
  if (( TEM_BREW == 1 )); then
    falta "git não está instalado" "é como o repositório é baixado" "rode: xcode-select --install"
  else
    falta "git não está instalado" "é como o repositório é baixado" "baixe em https://git-scm.com/downloads (no Windows, isso já traz o Git Bash)"
  fi
  falhas=$((falhas+1))
fi

NODE_VERSION="$(node -v 2>/dev/null)"; NODE_STATUS=$?
if [[ "$NODE_STATUS" == 0 && "$NODE_VERSION" =~ ^v([0-9]{1,3})\.[0-9]+\.[0-9]+$ ]] && (( 10#${BASH_REMATCH[1]} >= 24 )); then
  ok "node $NODE_VERSION"
else
  if (( TEM_BREW == 1 )); then
    falta "node ausente ou anterior à versão 24" "o instalador adaptativo do Core depende dela" "rode: brew install node"
  else
    falta "node ausente ou anterior à versão 24" "o instalador adaptativo do Core depende dela" "baixe em https://nodejs.org/ (versão 24 ou mais nova)"
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

if (( falhas > 0 )); then
  printf '\n  %s pré-requisito(s) faltando. Resolva os itens acima e rode de novo.\n\n' "$falhas" >&2
  exit 1
fi

# ── Login: só depois de confirmação explícita, e só se ausente ──────────
if ! gh auth status >/dev/null 2>&1; then
  if [[ ! -t 0 || ! -t 1 ]]; then
    falta "sem login e sem terminal interativo" "o login exige colar um código no navegador — precisa de um terminal de verdade" \
      "rode este comando num terminal interativo, ou autentique antes com: gh auth login"
    exit 1
  fi
  cat <<'LOGIN'

  Falta o login. Vai abrir o navegador e mostrar um código de 8 caracteres
  aqui no terminal — é só colar lá e autorizar.

LOGIN
  read -r -p "  Continuar? [S/n] " r
  [[ "${r:-s}" =~ ^[SsYy]?$ ]] || { echo "  Cancelado."; exit 0; }
  gh auth login --web --git-protocol https || { falta "o login não foi concluído" "sem ele não há como baixar um repositório privado" "rode: gh auth login"; exit 1; }
fi
ok "login presente"


# Acesso ao repositório é conferido à parte do login: sessão válida não é
# permissão de leitura neste repositório específico.
if ! gh repo view "$REPO" --json nameWithOwner >/dev/null 2>&1; then
  falta "sem acesso de leitura a $REPO" "o login funcionou, mas esta conta ainda não tem permissão neste repositório" \
    "peça acesso de leitura a $REPO a quem te entregou isto"
  exit 1
fi
ok "acesso a $REPO confirmado"

# ── Destino: sem migração de ~/.prima, sem fetch/merge automático ───────
# Uma árvore existente é do usuário; mexer nela sem pedir quebra confiança
# na primeira execução.
verificar_ancestrais_symlink() {
  local atual="$1" pai
  while [[ "$atual" != "/" && "$atual" != "." && -n "$atual" ]]; do
    [[ -L "$atual" ]] && return 1
    pai="$(dirname "$atual")"
    [[ "$pai" == "$atual" ]] && break
    atual="$pai"
  done
  [[ -L "/" ]] && return 1
  return 0
}

if ! verificar_ancestrais_symlink "$DESTINO"; then
  falta "o caminho de destino passa por um link simbólico" "isso pode apontar para fora do lugar esperado, sem avisar" \
    "aponte SEXTOU_CORE para um caminho real, sem links simbólicos no meio"
  exit 1
fi

if [[ -e "$DESTINO" && ! -d "$DESTINO" ]]; then
  falta "DESTINO_INVALIDO" "o destino não é diretório" "escolha outro caminho sem apagar o arquivo existente"; exit 1
fi
if [[ -e "$DESTINO" ]]; then
  if [[ -d "$DESTINO/.git" || -f "$DESTINO/.git" ]]; then
    [[ "$(git -C "$DESTINO" rev-parse --is-inside-work-tree 2>/dev/null)" == true ]] || { falta "CHECKOUT_INVALIDO" "Git não reconhece esta árvore" "preserve o diretório e revise sua origem"; exit 1; }
    REMOTO="$(git -C "$DESTINO" remote get-url origin 2>/dev/null || true)"
    case "$REMOTO" in
      "https://github.com/$REPO.git"|"https://github.com/$REPO"|"git@github.com:$REPO.git"|"ssh://git@github.com/$REPO.git") ;;
      *)
        falta "existe algo em $DESTINO, mas não é um checkout de $REPO" \
          "o remoto configurado é diferente do esperado (ou não existe)" \
          "mova $DESTINO para outro lugar, ou aponte SEXTOU_CORE para outro caminho, e rode de novo"
        exit 1 ;;
    esac
  elif [[ -n "$(ls -A "$DESTINO" 2>/dev/null)" ]]; then
    falta "existe algo em $DESTINO que não é um checkout git" "não dá para saber se é seguro sobrescrever" \
      "esvazie $DESTINO manualmente, ou aponte SEXTOU_CORE para outro caminho, e rode de novo"
    exit 1
  fi
fi

# ── Baixar (só quando não há checkout ainda) ─────────────────────────────
if [[ -d "$DESTINO/.git" || -f "$DESTINO/.git" ]]; then
  ok "checkout existente reconhecido em $DESTINO (git não foi tocado)"
else
  echo "  Baixando..."
  mkdir -p "$(dirname "$DESTINO")" || exit 1
  if ! git -c credential.helper= -c 'credential.helper=!gh auth git-credential' clone --quiet "https://github.com/$REPO.git" "$DESTINO" 2>/dev/null; then
    falta "não consegui baixar o repositório" \
      "ou o seu acesso ainda não foi liberado, ou o nome do repositório mudou" \
      "peça acesso de leitura a $REPO a quem te entregou isto"
    exit 1
  fi
  ok "baixado em $DESTINO"
fi

# ── Instalador adaptativo: candidato, sem fallback para caminho legado ───
ADAPTATIVO="$DESTINO/instalador/instalar.sh"
if [[ ! -f "$ADAPTATIVO" || -L "$ADAPTATIVO" || ! -f "$DESTINO/instalador/instalar-adaptativo.mjs" || -L "$DESTINO/instalador/instalar-adaptativo.mjs" ]] || ! verificar_ancestrais_symlink "$ADAPTATIVO"; then
  printf '\n  %s✗ ADAPTIVE_INSTALLER_UNAVAILABLE%s\n' "$E" "$F" >&2
  printf '    %spor quê:%s este checkout do Core ainda não tem o instalador adaptativo candidato\n' "$D" "$F" >&2
  printf '    %so que fazer:%s atualize o checkout (%s) para uma versão que inclua instalador/instalar-adaptativo.mjs e rode de novo\n\n' "$D" "$F" "$DESTINO" >&2
  exit 1
fi

# ── Delegação: array, sem eval, prévia apenas ────────────────────────────
ARGS=(--adaptativo)
[[ -n "$PROVEDOR" ]] && ARGS+=(--provedor "$PROVEDOR")

cat <<'ANTES'

  Agora a prévia, dentro do Core: o que foi baixado é código; o que vier
  a seguir é o diagnóstico do instalador adaptativo — provedor,
  configuração. Autenticação e capacidades ainda precisam de prova operacional.

ANTES

bash "$ADAPTATIVO" "${ARGS[@]}"
status=$?

# Contrato com o Core: 0 é prévia concluída; 130 é cancelamento explícito;
# qualquer outro valor é falha. Só o primeiro libera a instrução de aplicação.
if (( status != 0 )); then
  if (( status == 130 )); then
    printf '\n  instalação cancelada. Nada foi aplicado.\n' >&2
    exit 130
  fi
  printf '\n  a prévia do instalador adaptativo terminou com falha (código %s).\n' "$status" >&2
  exit "$status"
fi

APLICAR_ARGS=(--adaptativo --aplicar)
[[ -n "$PROVEDOR" ]] && APLICAR_ARGS+=(--provedor "$PROVEDOR")

CMD_EXIBIDO="bash $(printf '%q' "$ADAPTATIVO")"
for a in "${APLICAR_ARGS[@]}"; do CMD_EXIBIDO+=" $(printf '%q' "$a")"; done

cat <<TEXTOFINAL

  Isto foi só a prévia (config-preview): nada foi aplicado. Se estiver de
  acordo, aplique de verdade com:

      $CMD_EXIBIDO

TEXTOFINAL
