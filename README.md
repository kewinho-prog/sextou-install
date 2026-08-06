# Instalar a Prima

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kewinho-prog/prima-install/main/install.sh)"
```

O que vai acontecer:

1. **Confere o que falta** e para, mostrando o comando exato. Não instala nada à força.
2. **Pede seu login** no repositório, pelo navegador. É o único jeito de baixar um repositório privado; o acesso fica no chaveiro do seu computador.
3. **Baixa** em `~/.prima/core`.
4. **Mostra tudo que mudaria** — e não muda nada.
5. Você confere e roda de novo com `--aplicar`.
6. Termina com `prima ola`.

Leva alguns minutos e **não precisa de chave nenhuma**. O modelo local (~6 GB) é um segundo passo, separado, conduzido pelo próprio roadmap depois da instalação.

---

**Este repositório contém apenas o `install.sh`.** Nenhuma capacidade, nenhum motor, nenhuma regra. Ele é público só porque o servidor de arquivos brutos não entrega repositório privado sem autenticação — e a instalação precisa começar de algum lugar.

Precisa de macOS, `git`, Node 20+, o cliente `gh` e o agente de terminal principal. O script confere tudo isso antes de qualquer coisa.
