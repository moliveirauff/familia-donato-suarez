# Claude Code - Projeto Família Donato Suarez

## 📋 Sobre o Projeto

Este é o **Hub da Família Donato Suarez** - uma coleção de dashboards web para rastreamento e gestão familiar.

- **Proprietário:** Mauricio Suarez (moliveirauff)
- **Repositório:** https://github.com/moliveirauff/familia-donato-suarez
- **Deploy:** GitHub Pages (https://moliveirauff.github.io/familia-donato-suarez/)

## 🏗️ Arquitetura

### Dashboards Ativos

1. **Matheus (Mamadas)** - `matheus.html`
   - Registro de alimentação do bebê
   - Dados: `data/mamadas.json`
   
2. **Matheus (Crescimento)** - `matheus-crescimento.html`
   - Curvas de peso e altura (OMS)
   - Dados: `data/matheus-crescimento.json`, `data/peso-referencia.json`, `data/altura-referencia.json`

3. **Lista de Compras** - `compras.html`
   - Gerenciamento de compras da família
   - Dados: `data/compras.json`

4. **Receitas** - `receitas.html`
   - Livro de receitas familiar
   - Dados: `data/receitas.json`

5. **Viagem** - `viagem.html`
   - Checklist para viagens
   - Dados: `data/viagem.json`

### Portal Central
- `index.html` - Hub principal com links para todos os dashboards
- Design: Cards responsivos, tema azul (#007bff)

## 🎨 Design System

**Cores:**
- Primária: `#007bff` (azul)
- Secundária: `#6c757d` (cinza)
- Sucesso: `#28a745` (verde)
- Aviso: `#ffc107` (amarelo)
- Perigo: `#dc3545` (vermelho)

**Tipografia:**
- Fonte: `'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
- Títulos: Bold
- Corpo: Regular

**Layout:**
- Mobile-first (responsivo)
- Grid de cards
- Padding/Margin: múltiplos de 8px

**Bibliotecas:**
- Chart.js para gráficos
- Bootstrap (opcional, depende do dashboard)

## 📂 Estrutura de Dados

Todos os arquivos JSON seguem estrutura array de objetos:

```json
[
  {
    "campo1": "valor",
    "campo2": "valor"
  }
]
```

**Backup:** Cada JSON tem `.csv` correspondente em `data/`

## 🔄 Workflow de Deploy

1. Editar arquivos localmente
2. Commit para `main` branch
3. GitHub Pages auto-atualiza (build automático)

**Scripts úteis:**
- Não há build step - HTML puro
- Versionamento manual no código

## 🛡️ Regras

1. **Nunca deletar arquivos de dados** sem backup explícito
2. **Sempre validar JSON** antes de commit (use `jq` ou equivalente)
3. **Mobile-first** - testar responsividade
4. **Acessibilidade** - usar tags semânticas HTML5
5. **Performance** - evitar bibliotecas pesadas desnecessárias
6. **Commits descritivos** - prefixo: `feat:`, `fix:`, `update:`, `docs:`

## 🧪 Testes

Não há testes automatizados. Validar manualmente:
1. Abrir dashboard no navegador
2. Verificar carregamento de dados
3. Testar interatividade (se aplicável)
4. Verificar em mobile (DevTools)

## 📝 Convenções de Código

- **Indentação:** 2 espaços
- **HTML:** Lowercase para tags e atributos
- **CSS:** BEM ou classes descritivas simples
- **JS:** ES6+ (async/await, arrow functions)
- **Comentários:** Português ou Inglês (consistente por arquivo)

## 🚀 Como Adicionar Novo Dashboard

1. Criar `nome-dashboard.html` na raiz
2. Criar `data/nome-dashboard.json` com estrutura de dados
3. Adicionar card no `index.html` com link
4. Seguir design system existente
5. Commit e push

## 🔗 Links Úteis

- [Chart.js Docs](https://www.chartjs.org/docs/)
- [GitHub Pages](https://docs.github.com/pages)
- [MDN Web Docs](https://developer.mozilla.org/)

---

**Última atualização:** 2026-02-08
