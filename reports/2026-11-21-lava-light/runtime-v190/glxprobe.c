/* Minimal GLX probe: creates a 3.2 core... compat context on $DISPLAY and prints GL strings + renders/read-back one pixel. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <X11/Xlib.h>
#include <GL/gl.h>
#include <GL/glx.h>
int main(void){
  Display*d=XOpenDisplay(NULL); if(!d){puts("NO_DISPLAY");return 2;}
  int attr[]={GLX_RGBA,GLX_DOUBLEBUFFER,GLX_DEPTH_SIZE,24,None};
  XVisualInfo*vi=glXChooseVisual(d,DefaultScreen(d),attr); if(!vi){puts("NO_VISUAL");return 3;}
  Window root=DefaultRootWindow(d); XSetWindowAttributes sa; sa.colormap=XCreateColormap(d,root,vi->visual,AllocNone); sa.event_mask=0;
  Window w=XCreateWindow(d,root,0,0,256,256,0,vi->depth,InputOutput,vi->visual,CWColormap|CWEventMask,&sa);
  GLXContext c=glXCreateContext(d,vi,NULL,True); if(!c){puts("NO_CONTEXT");return 4;}
  if(!glXMakeCurrent(d,w,c)){puts("NO_CURRENT");return 5;}
  printf("GL_RENDERER=%s\nGL_VENDOR=%s\nGL_VERSION=%s\n",glGetString(GL_RENDERER),glGetString(GL_VENDOR),glGetString(GL_VERSION));
  glClearColor(1,0.5f,0.25f,1); glClear(GL_COLOR_BUFFER_BIT); unsigned char px[4]={0}; glReadPixels(10,10,1,1,GL_RGBA,GL_UNSIGNED_BYTE,px);
  printf("PIXEL=%d,%d,%d,%d\n",px[0],px[1],px[2],px[3]); glXSwapBuffers(d,w); return 0;}
