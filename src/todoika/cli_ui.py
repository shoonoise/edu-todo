import hashlib
import sys
import argparse
import toml
from datetime import datetime as dt
from typing import Optional

from rich.prompt import IntPrompt, Confirm, Prompt

from todoika.core import TasksList
from todoika.storage import Storage, SQLiteStorage, UserBuilder, TasksListBuilder, PSQLStorage
from todoika.users import User


class CLIHandler:
    def __init__(self, storage: Storage):
        self.user: Optional[User] = None
        self.current_list: Optional[TasksList] = None
        self.storage = storage
        self.user_builder = UserBuilder(storage)
        self.tasks_list_builder = TasksListBuilder(storage)

    def login(self):
        user_name = Prompt.ask('Enter your name')
        password_hash = hashlib.md5(Prompt.ask('Enter your password', password=True).encode()).hexdigest()
        if password_hash != self.storage.get_md5hash_by_name(user_name):
            print('Wrong username or password')
            return
        self.user = self.user_builder.build_by_name(user_name)
        self.current_list = self.tasks_list_builder.build(self.user.db_id, self.user.default_list_id)

    def register(self):
        user_name = Prompt.ask('Enter your name')
        password_hash = hashlib.md5(Prompt.ask('Enter your password', password=True).encode()).hexdigest()
        self.user = self.user_builder.build_new(user_name, password_hash)
        self.current_list = self.tasks_list_builder.build(self.user.db_id, self.user.default_list_id)

    def create_task(self):
        task_description = Prompt.ask('Task description')
        due_date = None

        if Confirm.ask("Add due date?", default=False):
            due_date = CLIHandler.ask_date('Set due date')
        self.current_list.add_task(task_description=task_description, due_date=due_date)

    def edit_description(self):
        task_id = self.get_task_id()
        new_description = Prompt.ask('New description')
        self.current_list.edit_task_description(task_id, new_description)

    def edit_status(self):
        task_id = self.get_task_id()
        status_id = IntPrompt.ask('You can choose 1 - DONE or 2 - NEW status', choices=["1", "2"])

        status_mapping = {
            1: "DONE",
            2: "NEW"
        }

        self.current_list.set_task_status(task_id, status_mapping[status_id])

    @classmethod
    def ask_date(cls, prompt: str) -> dt:
        date = Prompt.ask(f'{prompt} (format YYYY-MM-DD, H:M)')
        date_ts = dt.strptime(date, '%Y-%m-%d, %H:%M')
        return date_ts

    def edit_due_date(self):
        task_id = self.get_task_id()
        new_date = CLIHandler.ask_date('Set new date')
        self.current_list.set_due_date(task_id, new_date)

    def show_with_status(self, status, indexes=False):
        lines = []
        for i, t in enumerate(self.current_list.filter_tasks_by_status(status), start=1):
            due_date = t.due_date.strftime("%d.%m.%y - %H.%M") if t.due_date is not None else ""
            status = "☐" if t.status == "NEW" else "☑"

            if indexes:
                lines.append(f"{i} - {status} {t.description}\t{due_date}")
            else:
                lines.append(f"{status} {t.description}\t{due_date}")

        print("\n".join(lines))

    def get_main_menu_command(self):
        """main menu"""
        options = [
            "Commands:\n"
            "1: add new task",
            "2: edit description",
            "3: edit status",
            "4: edit due date",
            "5: show active tasks",
            f"6: show all tasks ({len(self.current_list)})",
            "7: show completed tasks",
            "8: quit\n"
        ]
        command = IntPrompt.ask("\n".join(options), choices=[str(opt) for opt in range(1, 9)],
                                show_choices=False)
        return command

    def get_task_id(self):
        """printing of task list to choosing task & UI processing"""
        self.show_with_status(None, indexes=True)
        task_id = IntPrompt.ask('Pick a task \n', choices=[str(i) for i in range(1, len(self.current_list) + 1)],
                                show_choices=False)
        return task_id - 1


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file')
    args: argparse.Namespace = parser.parse_args()

    conf = toml.load(args.config)

    if conf['database']['db_type'] == 'PSQL':
        active_storage = PSQLStorage(host=conf['database']['host'],
                                     user=conf['database']['user'],
                                     password=conf['database']['password'],
                                     db_name=conf['database']['db_name'],
                                     port=conf['database']['port'])
    elif conf['database']['db_type'] == 'SQLite':
        active_storage = SQLiteStorage(conf['database']['name'])
    else:
        raise RuntimeError(f"Unknown storage:{conf['database']['db_type']}")

    handler = CLIHandler(active_storage)

    while True:
        main_menu_command = None

        try:
            if not handler.user:
                init_cmd = IntPrompt.ask("Login (1) or Register (2) or Quit (3)", choices=["1", "2", "3"])
                cmd_mapping = {
                    1: handler.login,
                    2: handler.register,
                    3: sys.exit
                }
                cmd_mapping[init_cmd]()
                continue

            main_menu_command = handler.get_main_menu_command()

            if main_menu_command == 1:
                handler.create_task()
            elif main_menu_command == 2:
                handler.edit_description()
            elif main_menu_command == 3:
                handler.edit_status()
            elif main_menu_command == 4:
                handler.edit_due_date()
            elif main_menu_command == 5:
                handler.show_with_status('new')
            elif main_menu_command == 6:
                handler.show_with_status(None)
            elif main_menu_command == 7:
                handler.show_with_status('done')
            elif main_menu_command == 8:
                sys.exit(0)
        except KeyboardInterrupt:
            # `ctrl + c` - exit from sub-menu
            print(f"\nUndo cmd {main_menu_command}")
            continue
        except Exception as e:
            print(e)
