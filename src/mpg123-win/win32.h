#ifndef WIN32_H
#define WIN32_H

#ifdef WIN32
//#pragma warning(disable: 4068) // suppress 'unknown pragma'??
#define _CRT_SECURE_NO_DEPRECATE 1
#define strcasecmp strcmpi
#define strcmpi _strcmpi
#define strncasecmp strnicmp
#define snprintf _snprintf
#define read _read

#define ssize_t size_t
#define STDIN_FILENO  0
#define STDOUT_FILENO 1

#define OPT_GENERIC 1
#undef  HAVE_SETPRIORITY
#endif

#endif