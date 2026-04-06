# 📊 EstoquePro - Sistema de Gestão de Estoque

> Um sistema web moderno, robusto e escalável para controle total de estoque com dashboards executivos, inteligência de reposição e análises financeiras

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.13-336FA3?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**[Demonstração](#-demonstração) • [Instalação](#-como-executar-localmente) • [Recursos](#-funcionalidades) • [Tecnologias](#-tecnologias-utilizadas)**

</div>

---

## ✨ Funcionalidades

### 🎯 **Gestão Operacional**
- ✅ **Dashboard Executivo** com KPIs em tempo real (estoque, caixa, pendências, riscos)
- ✅ **Gestão de Produtos** com SKU, preços de custo/venda, categorias e fornecedores
- ✅ **Movimentações de Estoque** (entrada, saída, ajuste) com validações e rastreamento
- ✅ **Pedidos de Compra** com recebimento automático e entrada em estoque
- ✅ **Pedidos de Venda** com clientes e baixa automática de inventário
- ✅ **Controle por Lotes** com data de validade e alertas de expiração

### 💰 **Módulo Financeiro (Fase 3)**
- ✅ **Gestão de Receitas/Despesas** com status (pendente, pago, cancelado)
- ✅ **Fluxo de Caixa** com projeção de 14 dias
- ✅ **Análise de Pagamentos Atrasados** e alertas automáticos
- ✅ **Relatórios Financeiros** e KPIs consolidados

### 📦 **Inteligência de Reposição**
- ✅ **Classificação ABC** de produtos por valor de vendas
- ✅ **Recomendações de Reposição** baseadas em histórico
- ✅ **Alertas de Ruptura de Estoque** com análise de risco
- ✅ **Cálculo Inteligente de Quantidade Alvo**

### 👥 **Controle de Acesso**
- ✅ **Sistema de Permissões Granular** (admin, operador com controles específicos)
- ✅ **Gestão de Usuários** com ativação/desativação dinâmica
- ✅ **Matriz de Permissões** personalizável por usuário
- ✅ **Auditoria Completa** de ações (criação, edição, exclusão)

### 📊 **Dados & Relatórios**
- ✅ **Exportação CSV** de produtos, movimentações e relatórios
- ✅ **Importação em Lote** de produtos via CSV com validação
- ✅ **Logs de Auditoria** com rastreamento de usuário, ação, endpoint e status
- ✅ **Paginação de Dados** com filtros avançados em todas as listas

### 🔒 **Segurança & Confiabilidade**
- ✅ **Backup Automático Diário** com histórico restorável
- ✅ **Backup Manual On-Demand** via interface
- ✅ **Restauração de Dados** simples e confiável
- ✅ **Proteção Anti-Lockout** (admin não pode remover permissões próprias)
- ✅ **Validação de Entrada** em todos os formulários

### 🎨 **Interface Moderna**
- ✅ **Design Responsivo** (mobile, tablet, desktop) com Bootstrap 5
- ✅ **Menu Dropdown Contextual** com z-index e sombras
- ✅ **Tipografia Moderna** (Manrope + Space Grotesk)
- ✅ **Animações Suaves** e transições fluidas
- ✅ **Modo Claro** otimizado para produtividade

---

## 🛠️ Tecnologias Utilizadas

### **Backend**
[![Python](https://img.shields.io/badge/Python%203.13-336FA3?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask%203.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy%203.1-CE422B?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org)

### **Frontend**
[![Bootstrap](https://img.shields.io/badge/Bootstrap%205.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com)
[![HTML5](https://img.shields.io/badge/HTML5-E34C26?style=for-the-badge&logo=html5&logoColor=white)](https://html.spec.whatwg.org)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://www.w3.org/Style/CSS/)
[![Jinja2](https://img.shields.io/badge/Jinja2-Templates-B41717?style=for-the-badge&logo=jinja&logoColor=white)](https://jinja.palletsprojects.com)

### **Ferramentas & Deployment**
[![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)](https://git-scm.com)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-EXE-2E3440?style=for-the-badge)](https://pyinstaller.org)
[![PowerShell](https://img.shields.io/badge/PowerShell-5671C5?style=for-the-badge&logo=powershell&logoColor=white)](https://learn.microsoft.com/powershell/)
[![Windows](https://img.shields.io/badge/Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)

### **Arquitetura**
- **Padrão MVC** com separação clara de responsabilidades
- **ORM SQLAlchemy** para abstração de dados
- **Blueprints Flask** para modularização de rotas
- **Session Management** com segurança e validação
- **Pool de Conexões** NullPool para SQLite

---

## 🚀 Como Executar Localmente

### 📋 Pré-requisitos

- **Windows 10+** ou Linux/macOS com Python
- **Python 3.13+** (ou qualquer ambiente Python 3.10+)
- **Git** para clonar o repositório
- **~100 MB** espaço em disco

### 💻 Instalação e Execução

#### **Opção 1: Executar como Aplicação Web (Recomendado para desenvolvimento)**

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/EstoquePro.git
cd EstoquePro

# 2. Crie um ambiente virtual (opcional, mas recomendado)
python -m venv venv

# 3. Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Execute a aplicação
python app.py

# 6. Acesse no navegador
# Abra: http://127.0.0.1:5000
```

#### **Opção 2: Executar como Aplicação Desktop (Windows)**

```powershell
# 1. Clone e entre no diretório
git clone https://github.com/seu-usuario/EstoquePro.git
cd EstoquePro

# 2. Instale dependências
pip install -r requirements.txt

# 3. Compile para executável
powershell -ExecutionPolicy Bypass -File build_desktop.ps1

# 4. Execute o aplicativo
.\dist\EstoquePro.exe
```

### 🔐 Acesso Inicial

| Campo | Valor |
|-------|-------|
| **Usuário** | `admin` |
| **Senha** | `admin123` |

⚠️ **Importante:** Altere a senha do administrador após o primeiro acesso em **Administração → Usuários**

### 📊 Verificar Banco de Dados

```bash
# Verificar status completo do banco
python check_db.py
```

---

## 📸 Screenshots

### Dashboard Executivo
![Dashboard](https://img.shields.io/badge/Dashboard%20com%20KPIs-Executivo-blue?style=for-the-badge)
- Visualização de estoque total, caixa, receitas/despesas pendentes
- Alertas de produtos com baixo estoque
- Produtos com vencimento próximo

### Gestão de Produtos
![Produtos](https://img.shields.io/badge/Produtos-Cadastro%20Management-blue?style=for-the-badge)
- CRUD completo com SKU, preços, categorias
- Filtros e paginação de dados
- Validação em tempo real

### Módulo Financeiro
![Financeiro](https://img.shields.io/badge/Financeiro-Receitas%20%26%20Despesas-green?style=for-the-badge)
- Gestão de receitas e despesas
- Fluxo de caixa com projeção
- Análise de pagamentos atrasados

### Reposição Inteligente
![Reposição](https://img.shields.io/badge/Reposição-Análise%20ABC-purple?style=for-the-badge)
- Classificação ABC de produtos
- Recomendações de reposição
- Alertas de ruptura de estoque

### Controle de Acesso
![Permissões](https://img.shields.io/badge/Permissões-Matriz%20de%20Acesso-orange?style=for-the-badge)
- Matriz de permissões customizável
- Gestão de usuários
- Histórico de auditoria completo

---

## 🌐 Demonstração

> **Em desenvolvimento:** Link de demonstração online será adicionado em breve.
> 
> Para testar localmente, siga as instruções de [instalação](#-como-executar-localmente)

---

## 📌 Sobre o Projeto

### 🎯 Objetivo
EstoquePro foi desenvolvido como um **sistema completo de gestão de estoque** que demonstra habilidades profissionais em:

- **Desenvolvimento Full-Stack**: Frontend responsivo + Backend robusto
- **Engenharia de Dados**: Gestão de banco de dados SQLite, relacionamentos complexos, integridade referencial
- **Automação de Processos**: Backup automático, importação em lote, baixa automática de estoque
- **Segurança & Compliance**: Auditoria completa, controle de acesso granular, proteção anti-lockout
- **UX/UI**: Interface moderna, responsiva, com design system consistente
- **DevOps & Deployment**: Build script PowerShell, compilação para EXE, gerenciamento de dependências

### 💼 Habilidades Demonstradas

#### Para **Suporte TI / Help Desk**
- Gestão de usuários e perfis de acesso
- Troubleshooting de conexão de banco
- Documentação clara e passo-a-passo
- Scripts de automação (PowerShell)
- Backup e recovery de dados

#### Para **Analista de Dados**
- Design de banco de dados relacional (15 tabelas)
- Análise de vendas (classificação ABC)
- Dashboards com KPIs
- Relatórios customizados
- Exportação e importação de dados

#### Para **Cloud / DevOps**
- Arquitetura modular e escalável
- Controle de versão (Git)
- Automação de build (PowerShell)
- Gestão de ambiente virtual
- Pool management de conexões

### 📈 Evolução do Projeto

**Fase 1 (MVP)**
- Dashboard, produtos, movimentações, compras, vendas, lotes

**Fase 2 (Produção)**
- Gestão de usuários com permissões, auditoria, backup/restore, importação CSV

**Fase 3 (Inteligência)**
- Módulo financeiro, replenishment AB análise, dashboard executivo

### 🏆 Diferenciais
- **Responsivo**: Mobile, tablet e desktop
- **Zero-Warning**: Código sem deprecation warnings (Python 3.13 compatible)
- **Produção-Ready**: Backup automático, auditoria, validações
- **Modular**: Fácil manutenção e extensão
- **Documentado**: README, docstrings, comentários claros

---

## 🔧 Estrutura do Projeto

```
EstoquePro/
├── inventory_app/              # Aplicação principal
│   ├── templates/              # Páginas HTML (Jinja2)
│   ├── static/
│   │   └── css/               # Estilos customizados
│   ├── models.py              # ORM - 15 tabelas (Users, Products, Orders, etc)
│   ├── routes.py              # 40+ endpoints Flask
│   ├── auth.py                # Autenticação e permissões
│   ├── backup_service.py      # Backup/restore automático
│   ├── phase1_service.py      # Lógica de operações
│   ├── phase2_service.py      # Auditoria e permissões
│   └── phase3_service.py      # Análise financeira e reposição
├── app.py                      # Entrypoint web
├── desktop_app.py              # Entrypoint desktop
├── build_desktop.ps1          # Script de build (PyInstaller)
└── requirements.txt            # Dependências
```

---

## 📝 Exemplos de Uso

### Criar um novo usuário
1. Login como **admin**
2. Acesse **Administração → Usuários**
3. Clique em **Novo Usuário**
4. Preencha dados e clique em **Salvar**

### Importar produtos via CSV
1. Acesse **Administração → Importação de Produtos**
2. Prepare arquivo com colunas: `sku`, `name`, `category`, `supplier`, `cost_price`, `sale_price`, `min_stock`
3. Upload do arquivo
4. Validação automática
5. Confirmação de importação

### Gerar relatório de vendas
1. Acesse **Operações → Vendas**
2. Use filtros para período desejado
3. Clique em **Exportar CSV**
4. Abra no Excel para análise avançada

### Restaurar backup
1. Acesse **Administração → Sistema**
2. Selecione backup desejado
3. Clique em **Restaurar**
4. Confirme a operação

---

## 🤝 Contribuições

Contribuições são bem-vindas! Para reportar bugs ou sugerir melhorias:

1. Abra uma **Issue** descrevendo o problema
2. Faça um **Fork** do projeto
3. Crie uma **Branch** para sua feature (`git checkout -b feature/AmazingFeature`)
4. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
5. Push para a Branch (`git push origin feature/AmazingFeature`)
6. Abra um **Pull Request**

---

## 📄 Licença

Este projeto é licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 💬 Dúvidas ou Sugestões?

Fique à vontade para abrir uma **Issue** ou entrar em contato:
- 💼 **LinkedIn**: [linkedin.com/in/matheus-lima-menezes](https://linkedin.com/in/matheus-lima-menezes)
- 📧 **Email**: matheuslimamenezes2005.com
- 🐙 **GitHub**: [@Zhennyn](https://github.com/Zhennyn)

---

<div align="center">

### Feito com ❤️ por Zhennyn

Desenvolvido com dedicação e atenção aos detalhes.

**Gostou do projeto? Deixe uma ⭐ e compartilhe!**

[![GitHub stars](https://img.shields.io/github/stars/seu-usuario/EstoquePro?style=social)](https://github.com/seu-usuario/EstoquePro)
[![GitHub forks](https://img.shields.io/github/forks/seu-usuario/EstoquePro?style=social)](https://github.com/seu-usuario/EstoquePro)
[![GitHub followers](https://img.shields.io/github/followers/seu-usuario?style=social)](https://github.com/seu-usuario)

</div>
