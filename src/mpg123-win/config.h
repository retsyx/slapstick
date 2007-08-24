/* basic config.h to reproduce pre-autoconf days */

#define GENERIC
#define OPT_I386
#define OPT_I486
#define HAVE_SYS_TYPES_H 1
//#define HAVE_SYS_WAIT_H
#define HAVE_SYS_TIME_H
//#define HAVE_SYS_RESOURCE_H

#if 1
//#define _CRT_SECURE_NO_DEPRECATE
#define NOXFERMEM

#endif
/* little automagic on its own for OSS header */
#ifdef LINUX
	#define HAVE_LINUX_SOUNDCARD_H
#elif defined(__bsdi__)
	#define HAVE_SYS_SOUNDCARD_H
#else
	#define HAVE_MACHINE_SOUNDCARD_H
#endif

/* C99 integer types header... needed for ID3 parsing */
#define HAVE_INTTYPES_H 1

/* aggresive and realtime options were enabled per default... unless for generic build */
#ifndef GENERIC
#define HAVE_SETPRIORITY
#ifndef NO_RT
	#define HAVE_SCHED_H
	#define HAVE_SCHED_SETSCHEDULER
#endif
#endif

#define INDEX_SIZE 1000
/* added by MakeLegacy.sh */
#define PACKAGE_NAME "mpg123"
#define PACKAGE_VERSION "0.66"
#define PACKAGE_BUGREPORT "mpg123-devel@lists.sourceforge.net"

#undef HAVE_SCHED_H