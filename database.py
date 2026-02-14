"""
Модуль для работы с базой данных SQLite.
Содержит класс Database с CRUD-операциями для всех сущностей.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с SQLite базой данных."""

    def __init__(self, db_path: str) -> None:
        """Инициализация подключения к БД."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        logger.info("База данных инициализирована: %s", db_path)

    def _create_tables(self) -> None:
        """Создание таблиц, если они не существуют."""
        cursor = self.conn.cursor()
        cursor.executescript("""
            -- Таблица пользователей
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                timezone TEXT DEFAULT 'Europe/Moscow',
                language_code TEXT DEFAULT 'ru',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Таблица команд
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                invite_code TEXT UNIQUE NOT NULL,
                subscription_type TEXT DEFAULT 'free',
                subscription_expires TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            );

            -- Таблица участников команд
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(team_id, user_id)
            );

            -- Таблица задач
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                assignee_id INTEGER,
                author_id INTEGER NOT NULL,
                deadline TIMESTAMP,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'todo',
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
                FOREIGN KEY (assignee_id) REFERENCES users(user_id),
                FOREIGN KEY (author_id) REFERENCES users(user_id)
            );

            -- Таблица комментариев к задачам
            CREATE TABLE IF NOT EXISTS comments (
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Таблица отправленных напоминаний
            CREATE TABLE IF NOT EXISTS reminders (
                reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                reminder_type TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            );

            -- Индексы для оптимизации
            CREATE INDEX IF NOT EXISTS idx_tasks_team ON tasks(team_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
            CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
        """)
        self.conn.commit()

    # ─── Пользователи ──────────────────────────────────────────────

    def add_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None = None,
        language_code: str = "ru",
    ) -> None:
        """Регистрация нового пользователя или обновление существующего."""
        try:
            self.conn.execute(
                """INSERT INTO users (user_id, username, first_name, last_name, language_code)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       username = excluded.username,
                       first_name = excluded.first_name,
                       last_name = excluded.last_name""",
                (user_id, username, first_name, last_name, language_code),
            )
            self.conn.commit()
            logger.info("Пользователь %s зарегистрирован / обновлён", user_id)
        except sqlite3.Error as e:
            logger.error("Ошибка регистрации пользователя: %s", e)

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        """Получение пользователя по ID."""
        return self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    def set_user_timezone(self, user_id: int, timezone: str) -> None:
        """Установка часового пояса пользователя."""
        self.conn.execute(
            "UPDATE users SET timezone = ? WHERE user_id = ?", (timezone, user_id)
        )
        self.conn.commit()

    # ─── Команды ────────────────────────────────────────────────────

    def create_team(self, name: str, owner_id: int, invite_code: str) -> int:
        """Создание новой команды. Возвращает team_id."""
        try:
            cursor = self.conn.execute(
                "INSERT INTO teams (name, owner_id, invite_code) VALUES (?, ?, ?)",
                (name, owner_id, invite_code),
            )
            team_id = cursor.lastrowid
            # Добавляем владельца как участника с ролью owner
            self.conn.execute(
                "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'owner')",
                (team_id, owner_id),
            )
            self.conn.commit()
            logger.info("Команда '%s' создана (ID=%s) владельцем %s", name, team_id, owner_id)
            return team_id
        except sqlite3.Error as e:
            logger.error("Ошибка создания команды: %s", e)
            return 0

    def get_team(self, team_id: int) -> Optional[sqlite3.Row]:
        """Получение команды по ID."""
        return self.conn.execute(
            "SELECT * FROM teams WHERE team_id = ?", (team_id,)
        ).fetchone()

    def get_team_by_invite(self, invite_code: str) -> Optional[sqlite3.Row]:
        """Получение команды по инвайт-коду."""
        return self.conn.execute(
            "SELECT * FROM teams WHERE invite_code = ?", (invite_code,)
        ).fetchone()

    def get_user_teams(self, user_id: int) -> list[sqlite3.Row]:
        """Получение всех команд пользователя."""
        return self.conn.execute(
            """SELECT t.* FROM teams t
               JOIN team_members tm ON t.team_id = tm.team_id
               WHERE tm.user_id = ?""",
            (user_id,),
        ).fetchall()

    def get_user_active_team(self, user_id: int) -> Optional[sqlite3.Row]:
        """Получение первой (активной) команды пользователя."""
        teams = self.get_user_teams(user_id)
        return teams[0] if teams else None

    # ─── Участники команд ──────────────────────────────────────────

    def add_team_member(
        self, team_id: int, user_id: int, role: str = "member"
    ) -> bool:
        """Добавление участника в команду."""
        try:
            self.conn.execute(
                "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, ?)",
                (team_id, user_id, role),
            )
            self.conn.commit()
            logger.info("Пользователь %s добавлен в команду %s", user_id, team_id)
            return True
        except sqlite3.IntegrityError:
            logger.warning("Пользователь %s уже в команде %s", user_id, team_id)
            return False
        except sqlite3.Error as e:
            logger.error("Ошибка добавления участника: %s", e)
            return False

    def remove_team_member(self, team_id: int, user_id: int) -> bool:
        """Удаление участника из команды."""
        try:
            self.conn.execute(
                "DELETE FROM team_members WHERE team_id = ? AND user_id = ?",
                (team_id, user_id),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Ошибка удаления участника: %s", e)
            return False

    def get_team_members(self, team_id: int) -> list[sqlite3.Row]:
        """Получение всех участников команды."""
        return self.conn.execute(
            """SELECT u.*, tm.role FROM users u
               JOIN team_members tm ON u.user_id = tm.user_id
               WHERE tm.team_id = ?
               ORDER BY tm.role DESC, tm.joined_at""",
            (team_id,),
        ).fetchall()

    def get_member_role(self, team_id: int, user_id: int) -> Optional[str]:
        """Получение роли пользователя в команде."""
        row = self.conn.execute(
            "SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
            (team_id, user_id),
        ).fetchone()
        return row["role"] if row else None

    def get_team_member_count(self, team_id: int) -> int:
        """Количество участников в команде."""
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ?", (team_id,)
        ).fetchone()
        return row["cnt"]

    # ─── Задачи ─────────────────────────────────────────────────────

    def create_task(
        self,
        team_id: int,
        title: str,
        author_id: int,
        description: str | None = None,
        assignee_id: int | None = None,
        deadline: str | None = None,
        priority: str = "medium",
    ) -> int:
        """Создание новой задачи. Возвращает task_id."""
        try:
            cursor = self.conn.execute(
                """INSERT INTO tasks
                   (team_id, title, description, assignee_id, author_id, deadline, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (team_id, title, description, assignee_id, author_id, deadline, priority),
            )
            self.conn.commit()
            task_id = cursor.lastrowid
            logger.info("Задача #%s создана в команде %s", task_id, team_id)
            return task_id
        except sqlite3.Error as e:
            logger.error("Ошибка создания задачи: %s", e)
            return 0

    def get_task(self, task_id: int) -> Optional[sqlite3.Row]:
        """Получение задачи по ID."""
        return self.conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()

    def get_user_tasks(
        self, user_id: int, team_id: int, status_filter: str | None = None
    ) -> list[sqlite3.Row]:
        """Получение задач пользователя в команде."""
        query = "SELECT * FROM tasks WHERE assignee_id = ? AND team_id = ?"
        params: list[Any] = [user_id, team_id]
        # Фильтруем по статусу, если указан
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY deadline ASC NULLS LAST"
        return self.conn.execute(query, params).fetchall()

    def get_team_tasks(
        self, team_id: int, status_filter: str | None = None
    ) -> list[sqlite3.Row]:
        """Получение всех задач команды."""
        query = "SELECT * FROM tasks WHERE team_id = ?"
        params: list[Any] = [team_id]
        # Фильтруем по статусу, если указан
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY deadline ASC NULLS LAST"
        return self.conn.execute(query, params).fetchall()

    def get_tasks_today(self, team_id: int) -> list[sqlite3.Row]:
        """Получение задач на сегодня."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.conn.execute(
            """SELECT * FROM tasks
               WHERE team_id = ? AND DATE(deadline) = ?
               AND status NOT IN ('done', 'cancelled')
               ORDER BY deadline ASC""",
            (team_id, today),
        ).fetchall()

    def get_tasks_week(self, team_id: int) -> list[sqlite3.Row]:
        """Получение задач на текущую неделю."""
        today = datetime.now()
        week_end = today + timedelta(days=7)
        return self.conn.execute(
            """SELECT * FROM tasks
               WHERE team_id = ?
               AND deadline BETWEEN ? AND ?
               AND status NOT IN ('done', 'cancelled')
               ORDER BY deadline ASC""",
            (team_id, today.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")),
        ).fetchall()

    def update_task_status(self, task_id: int, status: str) -> bool:
        """Обновление статуса задачи."""
        try:
            now = datetime.now().isoformat()
            completed_at = now if status == "done" else None
            self.conn.execute(
                """UPDATE tasks SET status = ?, updated_at = ?,
                   completed_at = COALESCE(?, completed_at)
                   WHERE task_id = ?""",
                (status, now, completed_at, task_id),
            )
            self.conn.commit()
            logger.info("Статус задачи #%s изменён на '%s'", task_id, status)
            return True
        except sqlite3.Error as e:
            logger.error("Ошибка обновления статуса: %s", e)
            return False

    def update_task(self, task_id: int, **kwargs) -> bool:
        """Обновление полей задачи."""
        try:
            allowed = {"title", "description", "assignee_id", "deadline", "priority", "tags"}
            fields = {k: v for k, v in kwargs.items() if k in allowed}
            # Проверяем что есть что обновлять
            if not fields:
                return False
            fields["updated_at"] = datetime.now().isoformat()
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [task_id]
            self.conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE task_id = ?", values
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Ошибка обновления задачи: %s", e)
            return False

    def delete_task(self, task_id: int) -> bool:
        """Удаление задачи."""
        try:
            self.conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            self.conn.commit()
            logger.info("Задача #%s удалена", task_id)
            return True
        except sqlite3.Error as e:
            logger.error("Ошибка удаления задачи: %s", e)
            return False

    def get_active_tasks_count(self, team_id: int) -> int:
        """Количество активных задач в команде."""
        row = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE team_id = ? AND status IN ('todo', 'in_progress')""",
            (team_id,),
        ).fetchone()
        return row["cnt"]

    # ─── Комментарии ────────────────────────────────────────────────

    def add_comment(self, task_id: int, user_id: int, text: str) -> int:
        """Добавление комментария к задаче."""
        try:
            cursor = self.conn.execute(
                "INSERT INTO comments (task_id, user_id, text) VALUES (?, ?, ?)",
                (task_id, user_id, text),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error("Ошибка добавления комментария: %s", e)
            return 0

    def get_task_comments(self, task_id: int) -> list[sqlite3.Row]:
        """Получение комментариев к задаче."""
        return self.conn.execute(
            """SELECT c.*, u.first_name, u.username FROM comments c
               JOIN users u ON c.user_id = u.user_id
               WHERE c.task_id = ?
               ORDER BY c.created_at ASC""",
            (task_id,),
        ).fetchall()

    # ─── Напоминания ────────────────────────────────────────────────

    def is_reminder_sent(self, task_id: int, reminder_type: str) -> bool:
        """Проверка, было ли отправлено напоминание."""
        row = self.conn.execute(
            "SELECT 1 FROM reminders WHERE task_id = ? AND reminder_type = ?",
            (task_id, reminder_type),
        ).fetchone()
        return row is not None

    def mark_reminder_sent(self, task_id: int, reminder_type: str) -> None:
        """Отметка об отправленном напоминании."""
        try:
            self.conn.execute(
                "INSERT INTO reminders (task_id, reminder_type) VALUES (?, ?)",
                (task_id, reminder_type),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error("Ошибка записи напоминания: %s", e)

    def get_upcoming_tasks(
        self, start: str, end: str
    ) -> list[sqlite3.Row]:
        """Получение задач с дедлайнами в указанном временном окне."""
        return self.conn.execute(
            """SELECT t.*, tm.name as team_name FROM tasks t
               JOIN teams tm ON t.team_id = tm.team_id
               WHERE t.status IN ('todo', 'in_progress')
               AND t.deadline BETWEEN ? AND ?""",
            (start, end),
        ).fetchall()

    def get_overdue_tasks(self) -> list[sqlite3.Row]:
        """Получение просроченных задач."""
        now = datetime.now().isoformat()
        return self.conn.execute(
            """SELECT * FROM tasks
               WHERE status IN ('todo', 'in_progress')
               AND deadline < ?
               ORDER BY deadline ASC""",
            (now,),
        ).fetchall()

    # ─── Статистика ─────────────────────────────────────────────────

    def get_team_stats(self, team_id: int) -> dict[str, Any]:
        """Получение статистики команды."""
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()

        # Общее количество задач
        total = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE team_id = ?", (team_id,)
        ).fetchone()["cnt"]

        # Активные задачи
        active = self.get_active_tasks_count(team_id)

        # Выполнено за неделю
        done_week = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE team_id = ? AND status = 'done' AND completed_at >= ?""",
            (team_id, week_ago),
        ).fetchone()["cnt"]

        # Выполнено за месяц
        done_month = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE team_id = ? AND status = 'done' AND completed_at >= ?""",
            (team_id, month_ago),
        ).fetchone()["cnt"]

        # Просроченные задачи
        now = datetime.now().isoformat()
        overdue = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE team_id = ? AND status IN ('todo', 'in_progress')
               AND deadline < ?""",
            (team_id, now),
        ).fetchone()["cnt"]

        # Топ-3 активных участников за неделю
        top_members = self.conn.execute(
            """SELECT u.first_name, u.username, COUNT(*) as cnt
               FROM tasks t JOIN users u ON t.assignee_id = u.user_id
               WHERE t.team_id = ? AND t.status = 'done' AND t.completed_at >= ?
               GROUP BY t.assignee_id
               ORDER BY cnt DESC LIMIT 3""",
            (team_id, week_ago),
        ).fetchall()

        return {
            "total": total,
            "active": active,
            "done_week": done_week,
            "done_month": done_month,
            "overdue": overdue,
            "top_members": top_members,
        }

    def get_user_stats(self, user_id: int, team_id: int) -> dict[str, Any]:
        """Получение личной статистики пользователя."""
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        now = datetime.now().isoformat()

        # Выполнено задач
        done = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE assignee_id = ? AND team_id = ? AND status = 'done'""",
            (user_id, team_id),
        ).fetchone()["cnt"]

        # В работе
        in_progress = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE assignee_id = ? AND team_id = ? AND status = 'in_progress'""",
            (user_id, team_id),
        ).fetchone()["cnt"]

        # Ожидают выполнения
        todo = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE assignee_id = ? AND team_id = ? AND status = 'todo'""",
            (user_id, team_id),
        ).fetchone()["cnt"]

        # Выполнено за неделю
        done_week = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE assignee_id = ? AND team_id = ? AND status = 'done'
               AND completed_at >= ?""",
            (user_id, team_id, week_ago),
        ).fetchone()["cnt"]

        # Просроченные
        overdue = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE assignee_id = ? AND team_id = ?
               AND status IN ('todo', 'in_progress') AND deadline < ?""",
            (user_id, team_id, now),
        ).fetchone()["cnt"]

        # Процент выполнения в срок
        total_done = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE assignee_id = ? AND team_id = ? AND status = 'done'""",
            (user_id, team_id),
        ).fetchone()["cnt"]

        on_time = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM tasks
               WHERE assignee_id = ? AND team_id = ? AND status = 'done'
               AND (completed_at <= deadline OR deadline IS NULL)""",
            (user_id, team_id),
        ).fetchone()["cnt"]

        on_time_pct = round(on_time / total_done * 100) if total_done > 0 else 0

        return {
            "done": done,
            "in_progress": in_progress,
            "todo": todo,
            "done_week": done_week,
            "overdue": overdue,
            "on_time_pct": on_time_pct,
        }

    # ─── Подписки ───────────────────────────────────────────────────

    def update_subscription(
        self, team_id: int, sub_type: str, expires: str | None = None
    ) -> bool:
        """Обновление подписки команды."""
        try:
            self.conn.execute(
                """UPDATE teams SET subscription_type = ?, subscription_expires = ?
                   WHERE team_id = ?""",
                (sub_type, expires, team_id),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Ошибка обновления подписки: %s", e)
            return False

    def close(self) -> None:
        """Закрытие соединения с БД."""
        self.conn.close()
        logger.info("Соединение с БД закрыто")
