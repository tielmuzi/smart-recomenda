import { useEffect, useMemo, useState } from 'react';
import { Activity, ArrowRight, BarChart3, BookOpen, Check, ChevronRight, CircleHelp, Clock3, Compass, Eye, Filter, Heart, Home, LockKeyhole, Menu, Plus, RefreshCw, Search, Settings2, ShieldCheck, Sparkles, Star, Tag, ThumbsDown, Trash2, UserRound, X } from 'lucide-react';
import { ApiError, api } from './services/api';
import type { AuthUser, Content, ContentType, Metrics, PreferenceState } from './types';

const demoPrefs: PreferenceState = { types: ['Filme', 'Série', 'Música'], genres: ['Ficção científica', 'Tecnologia', 'Suspense'], languages: ['Português', 'Inglês'], blocked_ids: [], diversity: 'equilibrada' };
const types: ContentType[] = ['Filme', 'Série', 'Música', 'Notícia'];
const genres = ['Ficção científica', 'Tecnologia', 'Suspense', 'Drama', 'Documentário', 'Indie', 'Design', 'Cultura'];

function Logo() { return <div className="brand"><span className="brand-mark"><Sparkles size={17} /></span><span>Smart<span>Recomenda</span></span></div>; }
function Pill({ children, active = false, onClick }: { children: React.ReactNode; active?: boolean; onClick?: () => void }) { return <button className={`pill ${active ? 'active' : ''}`} onClick={onClick}>{children}</button>; }
function Rating({ value }: { value?: number }) { return <span className="rating"><Star size={14} fill="currentColor" /> {value ? value.toFixed(1) : 'Sem avaliação'}</span>; }
function ContentCard({ item, onOpen, onFavorite, compact = false }: { item: Content; onOpen: (item: Content) => void; onFavorite: (id: number) => void; compact?: boolean }) {
  return <article className={`content-card ${compact ? 'compact' : ''}`}>
    <button className="cover-button" onClick={() => onOpen(item)} aria-label={`Abrir detalhes de ${item.title}`}><img src={item.cover} alt={`Capa de ${item.title}`} /><span className="cover-type">{item.type}</span></button>
    <div className="card-body"><div className="card-topline"><span className="eyebrow">{item.year || 'Demonstração'}</span><button className="icon-button" onClick={() => onFavorite(item.id)} aria-label="Adicionar aos favoritos"><Heart size={17} /></button></div>
      <button className="title-button" onClick={() => onOpen(item)}>{item.title}</button><div className="meta-row"><Rating value={item.rating} /><span>{item.genres[0]}</span></div>
      {!compact && <p className="card-description">{item.reason || item.description}</p>}
    </div>
  </article>;
}

export default function App() {
  const [page, setPage] = useState(window.location.pathname || '/');
  const [contents, setContents] = useState<Content[]>([]);
  const [recommended, setRecommended] = useState<Content[]>([]);
  const [favorites, setFavorites] = useState<Content[]>([]);
  const [prefs, setPrefs] = useState<PreferenceState>(demoPrefs);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [selected, setSelected] = useState<Content | null>(null);
  const [query, setQuery] = useState('');
  const [activeType, setActiveType] = useState<ContentType | 'Todos'>('Todos');
  const [activeGenre, setActiveGenre] = useState<string>('Todos');
  const [activeLanguage, setActiveLanguage] = useState<string>('Todos');
  const [toast, setToast] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [authReady, setAuthReady] = useState(false);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [demoAccess, setDemoAccess] = useState(false);
  const [authChoice, setAuthChoice] = useState<'demo' | null>(null);
  const [authError, setAuthError] = useState('');
  const [user, setUser] = useState<AuthUser | null>(null);

  const navigate = (path: string) => { window.history.pushState({}, '', path); setPage(path); setMenuOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  useEffect(() => { const fn = () => setPage(window.location.pathname); window.addEventListener('popstate', fn); return () => window.removeEventListener('popstate', fn); }, []);
  useEffect(() => {
    let mounted = true;
    const loadSession = async () => {
      try {
        const config = await api.authConfig();
        if (!mounted) return;
        setAuthEnabled(config.enabled);
        setDemoAccess(config.demo_access);
        if (!config.enabled && !config.demo_access) {
          setAuthError('O login ainda não foi configurado neste ambiente.');
          return;
        }
        let authenticatedUser: AuthUser;
        try {
          authenticatedUser = await api.authMe();
        } catch (error) {
          if (!(error instanceof Error) || !('status' in error) || error.status !== 401) {
            setAuthError('Não foi possível validar a sessão. Tente novamente.');
          }
          return;
        }
        if (!mounted) return;
        if (authenticatedUser.demo && !authChoice && config.enabled) {
          setLoading(false);
          setAuthReady(true);
          return;
        }
        setUser(authenticatedUser);
        const [catalog, recs, saved, favs] = await Promise.all([
          api.contents(),
          api.recommendations(),
          api.preferences(),
          api.favorites(),
        ]);
        if (!mounted) return;
        setContents(catalog.items);
        setRecommended(recs.items);
        setPrefs(saved);
        setFavorites(favs);
      } catch {
        if (mounted) setAuthError('Não foi possível conectar ao serviço de autenticação.');
      } finally {
        if (mounted) {
          setLoading(false);
          setAuthReady(true);
        }
      }
    };
    void loadSession();
    return () => { mounted = false; };
  }, [authChoice]);
  useEffect(() => { if (toast) { const timer = setTimeout(() => setToast(''), 3200); return () => clearTimeout(timer); } }, [toast]);

  const filtered = useMemo(() => contents.filter((item) => (activeType === 'Todos' || item.type === activeType) && (activeGenre === 'Todos' || item.genres.includes(activeGenre)) && (activeLanguage === 'Todos' || item.language === activeLanguage) && (!query || `${item.title} ${item.description} ${item.genres.join(' ')}`.toLowerCase().includes(query.toLowerCase()))), [contents, activeType, activeGenre, activeLanguage, query]);
  const refreshRecommendations = async () => {
    const result = await api.recommendations();
    setRecommended(result.items);
  };
  const openItem = (item: Content) => {
    setSelected(item);
    void api.recordInteraction(item.id, 'view')
      .then(refreshRecommendations)
      .catch(() => setToast('Não foi possível salvar este sinal de visualização.'));
  };
  const favorite = async (id: number) => {
    try {
      const result = await api.toggleFavorite(id);
      const content = contents.find((item) => item.id === id);
      setFavorites((current) => result.favorite
        ? content && !current.some((item) => item.id === id) ? [...current, content] : current
        : current.filter((item) => item.id !== id));
      await refreshRecommendations();
      setToast(result.favorite ? 'Adicionado aos favoritos.' : 'Removido dos favoritos.');
    } catch {
      setToast('Não foi possível salvar o favorito.');
    }
  };
  const hideItem = async (id: number) => {
    try {
      await api.recordInteraction(id, 'hide');
      setSelected(null);
      await refreshRecommendations();
      setToast('Entendido. Este conteúdo não será recomendado novamente.');
    } catch {
      setToast('Não foi possível atualizar suas recomendações.');
    }
  };
  const savePrefs = async () => {
    try {
      await api.savePreferences(prefs);
      await refreshRecommendations();
      setToast('Preferências salvas. Suas recomendações foram recalculadas.');
    } catch {
      setToast('Não foi possível salvar as preferências.');
    }
  };
  const logout = async () => {
    try {
      await api.logout();
      if (demoAccess) {
        setUser(await api.authMe());
        return;
      }
      setUser(null);
      setContents([]);
      setRecommended([]);
      setFavorites([]);
    } catch {
      setToast('Não foi possível encerrar a sessão. Tente novamente.');
    }
  };

  if (!authReady || loading) return <AuthScreen loading />;
  if (!user) return <AuthScreen enabled={authEnabled} demoAccess={demoAccess} error={authError} onGuest={() => { setAuthError(''); setLoading(true); setAuthChoice('demo'); }} />;

  const navItems = [{ path: '/', label: 'Início', icon: Home }, { path: '/buscar', label: 'Explorar', icon: Compass }, { path: '/favoritos', label: 'Favoritos', icon: Heart }, { path: '/historico', label: 'Histórico', icon: Clock3 }];
  const title = page === '/' ? 'Seu próximo acerto começa aqui' : page === '/buscar' ? 'Explore sem ruído' : page === '/favoritos' ? 'Sua curadoria pessoal' : page === '/historico' ? 'O que passou pelo seu radar' : page === '/preferencias' ? 'Ajuste seu sinal' : page === '/perfil' ? 'Seu espaço, suas regras' : page === '/como-recomendamos' ? 'Transparência que orienta' : page === '/admin' ? 'Painel de operação' : 'Descubra novos sinais';

  return <div className="app-shell">
    <aside className={`sidebar ${menuOpen ? 'open' : ''}`}><div className="sidebar-head"><Logo /><button className="icon-button mobile-only" onClick={() => setMenuOpen(false)} aria-label="Fechar menu"><X /></button></div><p className="sidebar-label">NAVEGAÇÃO</p><nav>{navItems.map(({ path: itemPath, label, icon: Icon }) => <button key={itemPath} className={`nav-item ${page === itemPath ? 'active' : ''}`} onClick={() => navigate(itemPath)}><Icon size={18} />{label}{label === 'Favoritos' && favorites.length > 0 && <span className="nav-count">{favorites.length}</span>}</button>)}</nav><p className="sidebar-label">SISTEMA</p><nav><button className="nav-item" onClick={() => navigate('/preferencias')}><Settings2 size={18} />Preferências</button><button className="nav-item" onClick={() => navigate('/como-recomendamos')}><CircleHelp size={18} />Como recomendamos</button>{user.role === 'admin' && <button className="nav-item" onClick={() => navigate('/admin')}><BarChart3 size={18} />Painel administrativo</button>}</nav><div className="sidebar-bottom"><div className="privacy-note"><ShieldCheck size={18} /><div><strong>Privacidade por padrão</strong><small>Você controla seus sinais.</small></div></div><button className="profile-mini" onClick={() => navigate('/perfil')}><span className="avatar">{user.name.slice(0, 2).toUpperCase()}</span><span><strong>{user.name}</strong><small>Conta conectada</small></span><ChevronRight size={16} /></button></div></aside>
    <main className="main-content"><header className="topbar"><button className="icon-button mobile-only" onClick={() => setMenuOpen(true)} aria-label="Abrir menu"><Menu /></button><div className="global-search"><Search size={18} /><input value={query} onChange={(e) => { setQuery(e.target.value); if (page !== '/buscar') navigate('/buscar'); }} placeholder="Buscar filmes, músicas, temas..." aria-label="Busca global" /></div><div className="topbar-actions"><button className="text-button" onClick={() => navigate('/preferencias')}><Filter size={16} /> Personalizar</button>{!user.demo && <button className="text-button" onClick={logout}>Sair</button>}<button className="icon-button" onClick={() => navigate('/perfil')} aria-label="Abrir perfil"><UserRound size={18} /></button></div></header><div className="page-wrap"><div className="breadcrumbs"><span>SmartRecomenda</span><ChevronRight size={14} /><span>{page === '/' ? 'Início' : title}</span></div><section className="page-heading"><div><p className="kicker"><span className="signal-dot" /> {user.demo ? 'ACESSO ACADÊMICO · SEM LOGIN' : 'SINAL SMART · 08 OUT 2026'}</p><h1>{title}</h1><p className="heading-copy">{page === '/' ? 'Uma curadoria pessoal para você decidir em menos tempo e descobrir com mais intenção.' : 'Escolha o próximo caminho. Seus sinais continuam sob seu controle.'}</p></div>{page === '/' && <button className="primary-button" onClick={() => navigate('/preferencias')}>Ajustar preferências <ArrowRight size={17} /></button>}</section>
      {loading ? <div className="loading-state"><div className="spinner" /><p>Calculando seus sinais...</p></div> : <>{page === '/' && <HomePage recommended={recommended} contents={contents} favoritesCount={favorites.length} prefs={prefs} onOpen={openItem} onFavorite={favorite} onNavigate={navigate} />}{page === '/buscar' && <SearchPage items={filtered} activeType={activeType} activeGenre={activeGenre} activeLanguage={activeLanguage} setActiveType={setActiveType} setActiveGenre={setActiveGenre} setActiveLanguage={setActiveLanguage} onOpen={openItem} onFavorite={favorite} />}{page === '/favoritos' && <FavoritesPage items={favorites} onOpen={openItem} onFavorite={favorite} />}{page === '/historico' && <HistoryPage onClear={() => api.clearHistory().then(refreshRecommendations).then(() => setToast('Sinais de navegação apagados; notas e favoritos continuam salvos.')).catch(() => setToast('Não foi possível apagar os sinais de navegação.'))} />}{page === '/preferencias' && <PreferencesPage prefs={prefs} setPrefs={setPrefs} onSave={savePrefs} />}{page === '/perfil' && <ProfilePage user={user} onLogout={logout} onNavigate={navigate} />}{page === '/como-recomendamos' && <HowPage />}{page === '/admin' && (user.role === 'admin' ? <AdminPage metrics={metrics} setMetrics={setMetrics} onToast={setToast} /> : <EmptyState title="Acesso restrito" copy="Seu perfil não tem permissão para abrir o painel administrativo." />)}</>}</div><footer><span>SmartRecomenda © 2026 · Projeto acadêmico demonstrativo</span><span>Desenvolvido para Tecnologias Emergentes · <button onClick={() => navigate('/perfil')}>Privacidade</button></span></footer></main>
    {selected && <DetailModal item={selected} onClose={() => setSelected(null)} onFavorite={favorite} onHide={() => hideItem(selected.id)} onRate={(rating) => api.rate(selected.id, rating).then(refreshRecommendations).then(() => setToast('Avaliação registrada e usada nas próximas recomendações.')).catch(() => setToast('Não foi possível registrar a avaliação.'))} />}{toast && <div className="toast"><Check size={17} />{toast}</div>}
  </div>;
}

function AuthScreen({ loading = false, enabled = false, demoAccess = false, error = '', onGuest }: { loading?: boolean; enabled?: boolean; demoAccess?: boolean; error?: string; onGuest?: () => void }) {
  return <main className="auth-screen">
    <section className="auth-card">
      <Logo />
      <span className="banner-icon"><ShieldCheck size={23} /></span>
      <p className="eyebrow">SUA CONTA, SUAS RECOMENDAÇÕES</p>
      <h1>{loading ? 'Verificando sua sessão' : demoAccess ? 'Como você quer acessar?' : 'Entre para continuar'}</h1>
      <p>{loading ? 'Estamos preparando seu acesso seguro.' : demoAccess ? 'Escolha uma opção: entre para salvar sua curadoria em uma conta ou continue como visitante, sem criar login.' : 'Acesse sua curadoria, preferências e histórico com sua conta autenticada.'}</p>
      {loading ? <div className="spinner" /> : demoAccess
        ? <div className="auth-options"><button className="primary-button" onClick={onGuest}>Continuar sem login</button>{enabled && <a className="secondary-button auth-login" href={api.loginUrl}>Entrar com autenticação</a>}</div>
        : enabled
        ? <a className="primary-button auth-login" href={api.loginUrl}>Entrar com Auth</a>
        : <div className="auth-error">{error || 'O login ainda não está disponível.'}</div>}
      {error && enabled && <div className="auth-error">{error}</div>}
      <small>O SmartRecomenda não armazena sua senha. A sessão é protegida por cookie HTTP-only.</small>
    </section>
  </main>;
}

function SectionHeader({ eyebrow, title, action, onClick }: { eyebrow: string; title: string; action?: string; onClick?: () => void }) { return <div className="section-header"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{action && <button className="link-button" onClick={onClick}>{action} <ArrowRight size={15} /></button>}</div>; }
function HomePage({ recommended, contents, favoritesCount, prefs, onOpen, onFavorite, onNavigate }: { recommended: Content[]; contents: Content[]; favoritesCount: number; prefs: PreferenceState; onOpen: (i: Content) => void; onFavorite: (id: number) => void; onNavigate: (p: string) => void }) {
  const leadSignal = prefs.genres[0] || prefs.types[0] || 'seus interesses';
  const quickStats = [
    { label: 'Favoritos', value: String(favoritesCount) },
    { label: 'Tipos em foco', value: String(prefs.types.length) },
    { label: 'Seu principal sinal', value: leadSignal },
  ];

  return <div className="page-stack"><section className="signal-banner"><div><span className="banner-icon"><Sparkles size={23} /></span><div><p className="eyebrow">CURADORIA ATUALIZADA</p><h2>Seu sinal está ficando mais nítido.</h2><p>Preferências, avaliações, favoritos e itens que você abriu ajudam a criar uma curadoria explicável e cada vez mais alinhada a você.</p></div></div><button className="ghost-button" onClick={() => onNavigate('/como-recomendamos')}>Ver como funciona <ArrowRight size={15} /></button></section><section className="quick-stats">{quickStats.map((stat) => <div key={stat.label} className="stat-card"><small>{stat.label}</small><strong>{stat.value}</strong></div>)}</section><section><SectionHeader eyebrow="CURADORIA PARA AGORA" title="Recomendados para você" action="Ver todos" onClick={() => onNavigate('/buscar')} /><div className="card-grid">{recommended.slice(0, 4).map((item) => <ContentCard key={item.id} item={item} onOpen={onOpen} onFavorite={onFavorite} />)}</div></section><section><SectionHeader eyebrow="PONTO DE PARTIDA" title={`Por que explorar ${leadSignal}`} /><div className="reason-grid"><div className="reason-card blue"><Tag size={21} /><strong>Seus temas preferidos</strong><p>{prefs.genres.length ? `Você escolheu ${prefs.genres.slice(0, 2).join(' e ')}. Esses sinais ajudam a ordenar conteúdos relevantes para seu perfil.` : 'Suas preferências explícitas ainda estão abertas; suas avaliações e favoritos ajudam a encontrar um ponto de partida.'}</p><button onClick={() => onNavigate('/preferencias')}>Editar sinais <ArrowRight size={15} /></button></div><div className="reason-card purple"><Activity size={21} /><strong>{prefs.diversity === 'foco' ? 'Foco no conhecido' : prefs.diversity === 'exploradora' ? 'Janela para descobertas' : 'Diversidade equilibrada'}</strong><p>A lista usa suas ações salvas e suas escolhas para equilibrar afinidade, novidades e repetição.</p><button onClick={() => onNavigate('/como-recomendamos')}>Entender a lógica <ArrowRight size={15} /></button></div></div></section><section><SectionHeader eyebrow="PULSO DO CATÁLOGO" title="Em alta na comunidade" action="Explorar catálogo" onClick={() => onNavigate('/buscar')} /><div className="horizontal-grid">{contents.slice(4, 8).map((item) => <ContentCard key={item.id} item={item} onOpen={onOpen} onFavorite={onFavorite} compact />)}</div></section></div>; }function SearchPage({ items, activeType, activeGenre, activeLanguage, setActiveType, setActiveGenre, setActiveLanguage, onOpen, onFavorite }: { items: Content[]; activeType: ContentType | 'Todos'; activeGenre: string; activeLanguage: string; setActiveType: (x: ContentType | 'Todos') => void; setActiveGenre: (x: string) => void; setActiveLanguage: (x: string) => void; onOpen: (i: Content) => void; onFavorite: (id: number) => void }) { return <div className="page-stack"><div className="filter-panel"><div className="filter-bar"><span className="eyebrow">FILTRAR POR TIPO</span>{['Todos', ...types].map((type) => <Pill key={type} active={activeType === type} onClick={() => setActiveType(type as ContentType | 'Todos')}>{type}</Pill>)}</div><div className="chip-row"><span className="eyebrow">GÊNERO</span>{['Todos', ...genres].map((genre) => <Pill key={genre} active={activeGenre === genre} onClick={() => setActiveGenre(genre)}>{genre}</Pill>)}</div><div className="chip-row"><span className="eyebrow">IDIOMA</span>{['Todos', 'Português', 'Inglês'].map((language) => <Pill key={language} active={activeLanguage === language} onClick={() => setActiveLanguage(language)}>{language}</Pill>)}</div></div>{items.length ? <div className="card-grid">{items.map((item) => <ContentCard key={item.id} item={item} onOpen={onOpen} onFavorite={onFavorite} />)}</div> : <EmptyState title="Nenhum sinal encontrado" copy="Tente outra busca ou remova um filtro para ampliar o radar." />}</div>; }
function FavoritesPage({ items, onOpen, onFavorite }: { items: Content[]; onOpen: (i: Content) => void; onFavorite: (id: number) => void }) { return <div className="page-stack">{items.length ? <div className="card-grid">{items.map((item) => <ContentCard key={item.id} item={item} onOpen={onOpen} onFavorite={onFavorite} />)}</div> : <EmptyState title="Sua curadoria começa com um coração" copy="Salve conteúdos para montar uma lista que respeita o seu tempo." />}</div>; }
function HistoryPage({ onClear }: { onClear: () => void }) { return <div className="page-stack"><div className="history-panel"><div className="panel-icon"><Clock3 /></div><div><p className="eyebrow">SINAIS SOB SEU CONTROLE</p><h2>Seu histórico ajuda a personalizar as descobertas.</h2><p>Visualizações e itens ocultados alimentam as próximas recomendações. Você pode apagar esses sinais de navegação quando quiser; avaliações e favoritos continuam salvos separadamente.</p><button className="secondary-button" onClick={onClear}><Trash2 size={16} /> Apagar sinais de navegação</button></div></div></div>; }
function PreferencesPage({ prefs, setPrefs, onSave }: { prefs: PreferenceState; setPrefs: (p: PreferenceState) => void; onSave: () => void }) { const toggle = (key: 'types' | 'genres' | 'languages', value: string) => setPrefs({ ...prefs, [key]: prefs[key].includes(value as never) ? prefs[key].filter((v) => v !== value) : [...prefs[key], value] } as PreferenceState); return <div className="page-stack narrow"><div className="preference-panel"><p className="eyebrow">SEU SINAL</p><h2>O que combina com você?</h2><p>Selecione sinais explícitos. Eles têm mais peso do que inferências e podem ser removidos depois.</p><PreferenceGroup label="Quero descobrir" values={types} selected={prefs.types} onToggle={(v) => toggle('types', v)} /><PreferenceGroup label="Temas e gêneros" values={genres} selected={prefs.genres} onToggle={(v) => toggle('genres', v)} /><PreferenceGroup label="Idiomas" values={['Português', 'Inglês', 'Espanhol']} selected={prefs.languages} onToggle={(v) => toggle('languages', v)} /><div className="preference-row"><div><strong>Personalidade do radar</strong><small>Quanto espaço abrimos para novidades?</small></div><select value={prefs.diversity} onChange={(e) => setPrefs({ ...prefs, diversity: e.target.value as PreferenceState['diversity'] })}><option value="foco">Foco no conhecido</option><option value="equilibrada">Equilibrada</option><option value="exploradora">Exploradora</option></select></div><button className="primary-button" onClick={onSave}>Salvar preferências <Check size={17} /></button></div></div>; }
function PreferenceGroup({ label, values, selected, onToggle }: { label: string; values: string[]; selected: string[]; onToggle: (v: string) => void }) { return <div className="preference-group"><div className="preference-label"><strong>{label}</strong><small>{selected.length} selecionado(s)</small></div><div className="pill-wrap">{values.map((value) => <Pill key={value} active={selected.includes(value)} onClick={() => onToggle(value)}>{value}</Pill>)}</div></div>; }
function ProfilePage({ user, onNavigate, onLogout }: { user: AuthUser; onNavigate: (p: string) => void; onLogout: () => void }) { return <div className="page-stack narrow"><div className="profile-hero"><span className="avatar large">{user.name.slice(0, 2).toUpperCase()}</span><div><p className="eyebrow">{user.demo ? 'MODO DE AVALIAÇÃO' : 'CONTA CONECTADA'}</p><h2>{user.name}</h2><p>{user.email || user.user_id}</p></div><button className="secondary-button" onClick={() => onNavigate('/preferencias')}><Settings2 size={16} /> Editar preferências</button></div><div className="settings-list"><div><ShieldCheck size={18} /><div><strong>Privacidade primeiro</strong><small>{user.demo ? 'Demonstração compartilhada para facilitar a avaliação acadêmica.' : 'Nenhum dado sensível é usado para recomendar conteúdo.'}</small></div><Check className="status-ok" size={18} /></div><div><LockKeyhole size={18} /><div><strong>Acesso simplificado</strong><small>{user.demo ? 'Não é necessário criar conta ou senha para explorar o projeto.' : 'Login pelo provedor de identidade; nenhuma senha é armazenada pelo app.'}</small></div><Check className="status-ok" size={18} /></div><div><BookOpen size={18} /><div><strong>Política de privacidade</strong><small>Leia finalidades, retenção e seus controles.</small></div><button className="link-button">Ler política <ArrowRight size={15} /></button></div>{!user.demo && <button className="secondary-button" onClick={onLogout}>Encerrar sessão</button>}</div></div>; }
function HowPage() { return <div className="page-stack narrow"><div className="how-card"><span className="banner-icon"><Sparkles size={23} /></span><p className="eyebrow">SEM CAIXA-PRETA</p><h2>Como recomendamos</h2><p>As preferências que você escolheu são combinadas com sinais persistidos de avaliações, favoritos e conteúdos abertos. Você pode ocultar itens e ajustar a exploração a qualquer momento.</p><div className="formula"><span>S(u,i)</span><strong>=</strong><span className="formula-blue">0,44 × E</span><strong>+</strong><span className="formula-purple">0,34 × H</span><strong>+</strong><span className="formula-green">0,10 × Q + 0,12 × P</span></div><div className="explain-grid"><div><strong>E · escolha explícita</strong><p>Afinidade com gêneros, tipos e idiomas selecionados nas preferências.</p></div><div><strong>H · histórico pessoal</strong><p>Avaliações e favoritos fortalecem sinais; visualizações ajudam suavemente e itens vistos ou avaliados perdem posição.</p></div><div><strong>Q/P · qualidade e pulso</strong><p>Avaliação média do catálogo e popularidade normalizada equilibram descoberta com relevância.</p></div></div><div className="note"><ShieldCheck size={18} /><span>Avaliações baixas reduzem a afinidade de gêneros relacionados. “Não recomendar novamente” bloqueia aquele conteúdo para sua conta.</span></div></div></div>; }
function AdminPage({ metrics, setMetrics, onToast }: { metrics: Metrics | null; setMetrics: (m: Metrics) => void; onToast: (s: string) => void }) {
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<ContentType>('Filme');
  const [genresText, setGenresText] = useState('');
  const [language, setLanguage] = useState('Português');

  const refresh = async () => {
    setRefreshing(true);
    try {
      setMetrics(await api.metrics());
    } catch {
      onToast('Não foi possível carregar as métricas administrativas.');
    } finally {
      setRefreshing(false);
    }
  };
  useEffect(() => { void refresh(); }, []);

  const createContent = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    try {
      await api.adminCreate({
        title: title.trim(),
        description: description.trim(),
        type,
        genres: genresText.split(',').map((genre) => genre.trim()).filter(Boolean),
        language,
      });
      setTitle('');
      setDescription('');
      setGenresText('');
      await refresh();
      onToast('Conteúdo adicionado ao catálogo.');
    } catch {
      onToast('Não foi possível adicionar o conteúdo. Verifique os campos.');
    } finally {
      setSaving(false);
    }
  };

  const maxDaily = Math.max(1, ...(metrics?.daily_activity.map((item) => item.recommendations + item.interactions) || [1]));
  const formatDay = (day: string) => new Date(`${day}T00:00:00`).toLocaleDateString('pt-BR', { weekday: 'short' });
  const actionLabel: Record<string, string> = { view: 'visualizou', favorite: 'favoritou', unfavorite: 'removeu dos favoritos', rating: 'avaliou', hide: 'ocultou' };

  return <div className="page-stack">
    <section className="admin-toolbar">
      <div><p className="eyebrow">VISÃO OPERACIONAL</p><h2>Atividade dos últimos 30 dias</h2><p>Métricas agregadas do catálogo e dos sinais registrados pela comunidade.</p></div>
      <button className="secondary-button" onClick={() => void refresh()} disabled={refreshing}><RefreshCw size={15} className={refreshing ? 'spin-icon' : ''} /> Atualizar</button>
    </section>
    <div className="admin-grid">
      {[
        ['Conteúdos', metrics?.contents ?? '—', 'itens no catálogo'],
        ['Pessoas ativas', metrics?.active_users ?? '—', 'com atividade recente'],
        ['Visualizações', metrics?.views ?? '—', 'sinais persistidos'],
        ['Favoritos', metrics?.favorites ?? '—', 'salvamentos atuais'],
        ['Avaliações', metrics?.ratings ?? '—', 'notas registradas'],
        ['Recomendações', metrics?.recommendations ?? '—', 'solicitações em 30 dias'],
      ].map(([label, value, note]) => <div className="metric-card" key={label}><p className="eyebrow">{label}</p><strong>{value}</strong><small>{note}</small></div>)}
    </div>
    <div className="admin-insights">
      <section className="admin-table"><div className="section-header"><div><p className="eyebrow">TENDÊNCIA</p><h2>Atividade diária</h2></div><span className="status-badge"><span className="signal-dot" /> {metrics?.strategy || 'HybridStrategy'}</span></div>
        <div className="activity-chart">{(metrics?.daily_activity || []).map((day) => <div className="activity-day" key={day.day} title={`${day.recommendations} recomendações · ${day.interactions} interações`}><div className="activity-bar"><span className="bar-recommendations" style={{ height: `${Math.max(0, (day.recommendations / maxDaily) * 100)}%` }} /><span className="bar-interactions" style={{ height: `${Math.max(0, (day.interactions / maxDaily) * 100)}%` }} /></div><small>{formatDay(day.day)}</small></div>)}</div>
        <div className="chart-legend"><span><i className="legend-recommendations" /> Recomendações</span><span><i className="legend-interactions" /> Interações persistidas</span></div>
      </section>
      <section className="admin-table"><div className="section-header"><div><p className="eyebrow">DESEMPENHO</p><h2>Conteúdos em destaque</h2></div></div>
        {(metrics?.top_contents || []).length ? <div className="admin-list">{metrics?.top_contents.map((item) => <div className="admin-list-row" key={item.id}><div><strong>{item.title}</strong><small>{item.type} · {item.average_rating ? `${item.average_rating} / 5` : 'sem notas'}</small></div><span><Eye size={14} /> {item.views}</span><span><Heart size={14} /> {item.favorites}</span></div>)}</div> : <p className="admin-empty">Ainda não há atividade suficiente para classificar conteúdos.</p>}
      </section>
    </div>
    <section className="admin-table"><div className="section-header"><div><p className="eyebrow">CATÁLOGO</p><h2>Distribuição por categoria</h2></div><span className="status-badge">{metrics?.data_label || 'Aguardando dados'}</span></div>
      <div className="table-row table-head"><span>Categoria</span><span>Itens</span><span>Participação</span></div>
      {Object.entries(metrics?.categories || {}).map(([category, total]) => <div className="table-row" key={category}><span>{category}</span><span>{total}</span><span className="category-track"><i style={{ width: `${metrics?.contents ? (Number(total) / metrics.contents) * 100 : 0}%` }} /></span></div>)}
    </section>
    <section className="admin-table"><div className="section-header"><div><p className="eyebrow">SINAIS RECENTES</p><h2>Atividade da comunidade</h2></div></div>
      {(metrics?.recent_activity || []).length ? <div className="admin-list">{metrics?.recent_activity.map((item, index) => <div className="admin-activity-row" key={`${item.created_at}-${item.content_title}-${index}`}><span className="activity-icon">{item.kind === 'hide' ? <ThumbsDown size={15} /> : item.kind === 'view' ? <Eye size={15} /> : item.kind === 'favorite' ? <Heart size={15} /> : <Star size={15} />}</span><span><strong>{item.user_name || 'Pessoa usuária'}</strong> {actionLabel[item.kind] || 'interagiu com'} <b>{item.content_title}</b><small>{new Date(`${item.created_at.replace(' ', 'T')}Z`).toLocaleString('pt-BR')}</small></span></div>)}</div> : <p className="admin-empty">Os novos sinais aparecerão aqui conforme as pessoas usam o app.</p>}
    </section>
    <section className="admin-table"><div className="section-header"><div><p className="eyebrow">GESTÃO</p><h2>Adicionar conteúdo</h2></div></div>
      <form className="admin-content-form" onSubmit={(event) => void createContent(event)}>
        <label>Título<input required minLength={2} maxLength={120} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
        <label>Tipo<select value={type} onChange={(event) => setType(event.target.value as ContentType)}>{types.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="form-wide">Descrição<textarea required minLength={10} maxLength={500} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <label>Temas (separados por vírgula)<input required value={genresText} onChange={(event) => setGenresText(event.target.value)} placeholder="Ex.: Ficção científica, Drama" /></label>
        <label>Idioma<input required value={language} onChange={(event) => setLanguage(event.target.value)} /></label>
        <div className="form-wide"><button className="primary-button" type="submit" disabled={saving}><Plus size={16} /> {saving ? 'Salvando...' : 'Adicionar ao catálogo'}</button></div>
      </form>
    </section>
  </div>;
}
function EmptyState({ title, copy }: { title: string; copy: string }) { return <div className="empty-state"><Compass size={30} /><h2>{title}</h2><p>{copy}</p></div>; }
function DetailModal({ item, onClose, onFavorite, onRate, onHide }: { item: Content; onClose: () => void; onFavorite: (id: number) => void; onRate: (rating: number) => void; onHide: () => void }) { const [rating, setRating] = useState(item.rating || 0); return <div className="modal-backdrop" role="dialog" aria-modal="true"><div className="detail-modal"><button className="icon-button close-button" onClick={onClose} aria-label="Fechar detalhes"><X /></button><div className="detail-cover"><img src={item.cover} alt={`Capa de ${item.title}`} /></div><div className="detail-content"><p className="eyebrow">{item.type} · {item.year || 'Demonstração'}</p><h2>{item.title}</h2><div className="meta-row"><Rating value={item.rating} /><span>{item.genres.join(' · ')}</span></div><p>{item.description}</p><div className="reason-box"><Sparkles size={17} /><div><strong>Por que está aqui</strong><span>{item.reason || 'Este conteúdo combina com sinais do catálogo que você acompanha.'}</span></div></div><div className="detail-actions"><button className="primary-button" onClick={() => onFavorite(item.id)}><Heart size={16} /> Favoritar</button><div className="rate-control"><span>Sua avaliação</span><div>{[1, 2, 3, 4, 5].map((value) => <button key={value} className={value <= rating ? 'selected' : ''} onClick={() => { setRating(value); onRate(value); }} aria-label={`Avaliar com ${value} estrelas`}><Star size={19} fill="currentColor" /></button>)}</div></div></div><button className="not-interested-button" onClick={onHide}><ThumbsDown size={15} /> Não recomendar novamente</button></div></div></div>; }
