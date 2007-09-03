#ifndef __WCURSES_H
#define __WCURSES_H

typedef struct wcurses_t {
	HANDLE std_i, std_o, std_e;
	SMALL_RECT extent;
} wcurses_t;

int wcurses_init(wcurses_t *wc);
int wcurses_deinit(wcurses_t *wc);
int wcurses_move(wcurses_t *wc, COORD *xy);
int wcurses_getxy(wcurses_t *wc, COORD *xy);
int wcurses_getch(wcurses_t *wc, COORD *xy, int *ch);
int wcurses_noecho(wcurses_t *wc);
int wcurses_echo(wcurses_t *wc);
int wcurses_write_row_attrs(wcurses_t *wc, COORD *xy, int len, WORD *attrs);
int wcurses_write_row_chars(wcurses_t *wc, COORD *xy, int len, WORD *s);
int wcurses_get_screen_size(wcurses_t *wc, COORD *xy);

#endif