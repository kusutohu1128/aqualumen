// Capture the complete drawable of one private Minecraft window at 1440p even
// when the desktop is smaller. "name" retains the pixmap until stdin closes.
// "read" sends its actual BGRX pixels to stdout, optionally at a fixed rate.
#define _POSIX_C_SOURCE 200809L
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xcomposite.h>
#include <errno.h>
#include <stdio.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t stopping;
static void stop_after_frame(int signal_number) { (void)signal_number; stopping=1; }

int main(int argc,char **argv) {
    if(argc<3 || argc>6) return 2;
    Display *display=XOpenDisplay(NULL);
    if(!display) return 3;
    Drawable handle=strtoul(argv[2],NULL,0);
    if(!strcmp(argv[1],"name") || !strcmp(argv[1],"existing")) {
        int redirect=!strcmp(argv[1],"name");
        if(redirect) XCompositeRedirectWindow(display,handle,CompositeRedirectAutomatic);
        XSync(display,False);
        Pixmap pixmap=XCompositeNameWindowPixmap(display,handle);
        XSync(display,False);
        printf("%lu\n",pixmap);
        fflush(stdout);
        while(getchar()!=EOF) {}
        XFreePixmap(display,pixmap);
        if(redirect) XCompositeUnredirectWindow(display,handle,CompositeRedirectAutomatic);
    } else if(!strcmp(argv[1],"read")) {
        Window root;
        unsigned width,height,border,depth;
        int x,y;
        if(!XGetGeometry(display,handle,&root,&x,&y,&width,&height,&border,&depth)) return 4;
        if(depth!=24 && depth!=32) return 5;
        if(argc<5) return 2;
        unsigned insideWidth=strtoul(argv[3],NULL,10),insideHeight=strtoul(argv[4],NULL,10);
        if(!insideWidth || !insideHeight || width<insideWidth || height<insideHeight ||
           width-insideWidth>32 || height-insideHeight>32) return 9;
        x=(width-insideWidth)/2;y=(height-insideHeight)/2;
        width=insideWidth;height=insideHeight;
        int fps=argc==6?atoi(argv[5]):0;
        if(fps<0 || fps>60) return 6;
        struct sigaction ending={0};
        ending.sa_handler=stop_after_frame;
        sigemptyset(&ending.sa_mask);
        ending.sa_flags=SA_RESTART;
        if(sigaction(SIGTERM,&ending,NULL)!=0) return 10;
        struct timespec next;
        clock_gettime(CLOCK_MONOTONIC,&next);
        do {
            XImage *img=XGetImage(display,handle,x,y,width,height,AllPlanes,ZPixmap);
            if(!img || img->bits_per_pixel!=32 || img->byte_order!=LSBFirst || img->bytes_per_line!=4*(int)width) return 7;
            size_t bytes=(size_t)img->bytes_per_line*height;
            size_t sent=fwrite(img->data,1,bytes,stdout);
            XDestroyImage(img);
            if(sent!=bytes || fflush(stdout)==EOF) return 8;
            if(fps) {
                next.tv_nsec+=1000000000L/fps;
                if(next.tv_nsec>=1000000000L){++next.tv_sec;next.tv_nsec-=1000000000L;}
                while(clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&next,NULL)==EINTR) {}
            }
        } while(fps && !stopping);
    } else return 2;
    XCloseDisplay(display);
    return 0;
}
