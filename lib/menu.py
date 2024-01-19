from typing import Callable
from os import system

from lib.styling import colors


class MenuItem:
    
    def __init__(self, title:str, callback:Callable=None, callback_args:list=[]) -> None:
        self.title = title
        self._callback = callback
        self._callback_args = callback_args


class Menu:
    
    def __init__(self, title, exit_title='Exit', list_only=False) -> None:
        self.title = title
        self.exit_title = exit_title
        self.list_only = list_only
        self._items = []
        
    def add_item(self, item:MenuItem):
        self._items.append(item)
        
    def show(self):
        while True:
            system('clear')
            print_title = f' {colors.BOLD_WHITE}{self.title} '
            print(print_title)
            for _ in self.title:
                print('=', end='')
            print(f'==\n{colors.DEFAULT}')
            for i, item in enumerate(self._items, start=1):
                print(f'{i} : {item.title}')
            if self.list_only:
                break
            print(f'{i+1} : {self.exit_title}')
            choice = input('\n>>> ')
            try:
                int_choice = int(choice)
            except:
                continue
            if not int_choice in range(1, len(self._items) + 2):
                continue
            if int_choice == i+1:
                return -1
            selected_item = self._items[int_choice-1]
            if selected_item._callback:
                selected_item._callback(*selected_item._callback_args)
            return int_choice
            
    def print(self):
        system('clear')
        print(self.title, end='\n\n')
        for i, item in enumerate(self._items, start=1):
            print(f'{i} - {item.title}')
        print(f'{i+1} - {self.exit_title}')
        
        
def confirm_input(title:str, true_value:str, false_value:str):
    new_title = f'{title} [{true_value}/{false_value}]: '
    while True:
        user_input = input(new_title)
        if user_input == true_value:
            return True
        if user_input == false_value:
            return False
        
    
        