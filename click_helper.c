#include <ApplicationServices/ApplicationServices.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 3) {
        return 2;
    }

    double x = atof(argv[1]);
    double appleScriptY = atof(argv[2]);
    CGRect displayBounds = CGDisplayBounds(CGMainDisplayID());
    double displayHeight = displayBounds.size.height;
    double y = displayHeight - appleScriptY;
    CGPoint point = CGPointMake(x, y);

    CGEventRef down = CGEventCreateMouseEvent(
        NULL,
        kCGEventLeftMouseDown,
        point,
        kCGMouseButtonLeft
    );
    CGEventRef up = CGEventCreateMouseEvent(
        NULL,
        kCGEventLeftMouseUp,
        point,
        kCGMouseButtonLeft
    );
    if (!down || !up) {
        return 3;
    }

    CGEventPost(kCGHIDEventTap, down);
    usleep(50000);
    CGEventPost(kCGHIDEventTap, up);

    CFRelease(down);
    CFRelease(up);
    return 0;
}
