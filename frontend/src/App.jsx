import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const exampleQuestions = [
  "Какие разделы должны быть в пояснительной записке?",
  "Какие документы надо сдать?",
  "Какой объём должен быть у ПЗ?",
  "Покажи пример структуры презентации по НИР",
  "Что должно быть в промежуточном отчёте по НИР?"
];

function App() {
  const [email, setEmail] = useState("student@test.local");
  const [password, setPassword] = useState("student123");
  const [token, setToken] = useState(localStorage.getItem("rag_token") || "");

  const [query, setQuery] = useState(
    "К какому институту, кафедре и направлению подготовки относится рабочая программа дисциплины «Теория нейронных сетей»?"
  );

  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [classification, setClassification] = useState(null);
  const [searchInfo, setSearchInfo] = useState(null);

  const [loginStatus, setLoginStatus] = useState("");
  const [askStatus, setAskStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const getSourceTitle = (source) => {
    return (
      source.document_name ||
      source.file_name ||
      "Источник без названия"
    );
  };

  const getSourceFileName = (source) => {
    return source.file_name || "Файл не указан";
  };

  const getSourceLabel = (source) => {
    if (source.source_label) {
      return source.source_label;
    }

    if (source.is_normative) {
      return "Нормативный источник";
    }

    if (
      source.document_type === "example_report" ||
      source.document_type === "example_presentation"
    ) {
      return "Пример работы";
    }

    if (source.metadata_mode === "auto") {
      return "Дополнительный источник";
    }

    return "Дополнительный источник";
  };

  const getSourceScore = (source) => {
    if (source.score === null || source.score === undefined) {
      return "—";
    }

    return source.score;
  };

  const handleLogin = async () => {
    setLoginStatus("Выполняется вход...");

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          email,
          password
        })
      });

      const data = await response.json();

      if (!response.ok) {
        setLoginStatus("Вход не выполнен");
        return;
      }

      localStorage.setItem("rag_token", data.access_token);
      setToken(data.access_token);
      setLoginStatus("Вход выполнен");
    } catch (error) {
      setLoginStatus("Backend недоступен");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("rag_token");
    setToken("");
    setLoginStatus("");
    setAskStatus("");
    setAnswer("");
    setSources([]);
    setClassification(null);
    setSearchInfo(null);
  };

  const handleAsk = async () => {
    if (!token) {
      setAskStatus("Сначала выполните вход");
      return;
    }

    if (!query.trim()) {
      setAskStatus("Введите вопрос");
      return;
    }

    setIsLoading(true);
    setAskStatus("");
    setAnswer("");
    setSources([]);
    setClassification(null);
    setSearchInfo(null);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          query,
          request_id: `req_${Date.now()}`
        })
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMessage =
          data?.detail?.message ||
          data?.detail ||
          "Не удалось обработать запрос";

        setAskStatus(errorMessage);
        return;
      }

      setAnswer(data.answer || "");
      setSources(data.sources || []);
      setClassification(data.classification || null);
      setSearchInfo(data.search || null);
      setAskStatus("Ответ получен");
    } catch (error) {
      setAskStatus("Ошибка подключения к backend");
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleClick = (question) => {
    setQuery(question);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">RAG University Assistant</div>
          <div className="subtitle">
            Интеллектуальный помощник по документам НИР, ПЗ и защиты
          </div>
        </div>

        <div className={token ? "status-badge online" : "status-badge offline"}>
          <span className="status-dot"></span>
          {token ? "Пользователь авторизован" : "Требуется вход"}
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar">
          <section className="card user-card">
            <div className="card-title">Аккаунт</div>

            <label>Email</label>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="student@test.local"
            />

            <label>Пароль</label>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              placeholder="Введите пароль"
            />

            <div className="button-row">
              <button className="primary" onClick={handleLogin}>
                Войти
              </button>

              <button className="ghost" onClick={handleLogout}>
                Выйти
              </button>
            </div>

            {loginStatus && (
              <div className={token ? "login-message success" : "login-message"}>
                {loginStatus}
              </div>
            )}
          </section>

          <section className="card">
            <div className="card-title">Примеры вопросов</div>

            <div className="examples">
              {exampleQuestions.map((question) => (
                <button
                  key={question}
                  className="example-button"
                  onClick={() => handleExampleClick(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </section>

          <section className="card info-card">
            <div className="card-title">База знаний</div>

            <div className="knowledge-item">
              <span>Документы</span>
              <strong>8</strong>
            </div>

            <div className="knowledge-item">
              <span>Чанки</span>
              <strong>242</strong>
            </div>

            <div className="knowledge-item">
              <span>Хранилище</span>
              <strong>Qdrant</strong>
            </div>
          </section>
        </aside>

        <section className="main-panel">
          <div className="question-card">
            <div className="question-header">
              <h1>Задайте вопрос по документам</h1>
              <p>
                Система найдёт релевантные фрагменты в базе знаний и вернёт ответ с источниками.
              </p>
            </div>

            <textarea
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Например: какие разделы должны быть в ПЗ?"
            />

            <div className="actions">
              <button className="primary large" onClick={handleAsk} disabled={isLoading}>
                {isLoading ? "Идёт поиск..." : "Получить ответ"}
              </button>

              {askStatus && <span className="request-status">{askStatus}</span>}
            </div>
          </div>

          {(classification || searchInfo) && (
            <div className="result-meta">
              {classification && (
                <div className="meta-card">
                  <span>Классификация</span>
                  <strong>{classification.display_name}</strong>
                  <small>{classification.class_name}</small>
                </div>
              )}

              {searchInfo && (
                <div className="meta-card">
                  <span>Поиск</span>
                  <strong>{searchInfo.found ? "Фрагменты найдены" : "Не найдено"}</strong>
                  <small>Найдено чанков: {searchInfo.chunks_count}</small>
                </div>
              )}
            </div>
          )}

          {answer ? (
            <div className="result-section">
              <article className="answer-card">
                <div className="section-label">Ответ LLM на основе RAG-системы</div>
                <p>{answer}</p>
              </article>

              <article className="sources-card">
                <div className="section-label">Источники</div>

                <div className="sources-grid">
                  {sources.length === 0 && (
                    <div className="empty-source">Источники не найдены</div>
                  )}

                  {sources.map((source) => (
                    <div
                      className="source-item"
                      key={`${source.source_id}_${source.file_name || source.document_name}_${source.chunk_number}`}
                    >
                      <div>
                        <div className="source-top">
                          <span>[{source.source_id}]</span>
                          <strong>{getSourceTitle(source)}</strong>
                        </div>

                        <div className="source-file">
                          {getSourceFileName(source)}
                        </div>
                      </div>

                      <div className="source-footer">
                        <span>Чанк {source.chunk_number || "—"}</span>
                        <span>Score {getSourceScore(source)}</span>
                        <span>{getSourceLabel(source)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">?</div>
              <h2>Ответ появится здесь</h2>
              <p>
                Выполните вход и отправьте вопрос. Система покажет найденный ответ с источниками.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;