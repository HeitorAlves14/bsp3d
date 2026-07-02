#include <stdio.h>

int main() {
    float n1 = 15.0;
    float n2 = 20.0;
    float n3 = 12.0;
    float n4;

    n4 = (float) n2 / n1;
    printf("%f\n", n4);
    n4 = (float) n4 * n3;
    printf("%f\n", n4);
    return 0;
}