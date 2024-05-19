## Fastbin
`fastbin`은 0x20바이트 이상 0x80바이트 이하의 청크가 해제될 때 저장되는 bin이다. LIFO 구조이며, `malloc()`을 통해 할당 요청이 들어오면 가장 마지막에 들어온 청크가 가장 먼저 나간다.   
총 7개의 `fastbin`이 있고, `fastbinsY[0]`은 0x20바이트의 청크를, `fastbinsY[1]`은 0x30바이트의 청크를, ..., `fastbinsY[6]`은 0x80바이트의 청크를 저장한다.   
만약 크기가 0x20바이트인 청크 A, B, C를 순서대로 해제하면 `fastbin`은 다음과 같이 구성된다.
```c
fastbinsY[0]=C, C->fd=B, B->fd=A, A->fd=NULL;
```
여기서 한 번 `malloc(0x10)`을 호출하면 가장 마지막으로 들어간 청크가 할당된다.
```c
fastbinsY[0]=B, B->fd=A, A->fd=NULL;
```

## Double Free Bug
`Double Free Bug`는 한 번 해제된 청크가 다시 해제되는 버그를 말한다.

```c
// gcc -o dfb1 dfb1.c
#include <stdlib.h>
int main()
{
	char *ptr = malloc(32);
	char *ptr2 = malloc(32);
	
	free(ptr);
	free(ptr);
	
	return 0;
}
```

위 코드는 `ptr1`이 가리키는 청크를 두 번 해제하는 코드로, DFB를 유발하기 위해 작성되었다. 하지만 해당 코드의 실행 결과는 다음과 같다.
```
$ ./dfb1
* Error in `./dfb1': double free or corruption (fasttop): 0x0000000000602010 *
```
그 이유는 glibc 코드 내에서 DFB를 방지하는 코드가 존재하기 때문이다. DFB는 보안 취약점으로 악용될 수 있는 버그이므로, glibc 개발자들은 이를 mitigate하는 코드를 추가했다.
```
if (__builtin_expect (old == p, 0))
  {
    errstr = "double free or corruption (fasttop)";
    goto errout;
  }
```
위 코드는 `_int_free()`에 있는 코드로, `p`는 해제하고자 하는 청크의 포인터, `old`는 청크 `p`의 크기에 해당하는 `fastbin`의 포인터이다. 즉 `old`는 해당 `fastbin`에서 가장 마지막으로 들어온 청크를 의미한다.   

### Bypass DFB mitigation
하지만 `old` 포인터의 허점이 있는데, `p`와 `old`를 비교할 때 `old`는 오직 `fastbin`에서 가장 마지막에 들어온 청크만을 가리킨다. 즉 이 외에 다른 청크들에 대해 검사하지 않는다.   
예를 들어, `fastbin`이 아래와 같이 구성됐고, `free(A)`를 수행했다고 가정하자.
```c
fastbinsY[0]=C, C->fd=B, B->fd=A, A->fd=NULL;
```
그러면 `old`는 `fastbinsY[0]=C`이고, `p`는 `A`이다. 그러나 `old`가 나머지 해제된 청크 `B`, `A`에 대입되지 않으므로, 가장 마지막에 들어온 청크 `C`만 비교하게 된다. 따라서 해제된 청크에 `A`가 있음에도 청크 `A`를 한 번 더 해제할 수 있다.

```
// gcc -o dfb2 dfb2.c
#include <stdlib.h>

int main()
{
	char *ptr = malloc(32);     // 0x602010 
	char *ptr2 = malloc(32);    // 0x602030
	
	free(ptr);
  free(ptr2);
	free(ptr);
	
	return 0;
}
```
`dfb2`는 DFB를 유발하는 코드다. `ptr`이 가리키는 청크를 해제한 후, `ptr2`가 가리키는 청크를 해제하여 `old=0x602020`으로 설정한다. 이때 `free(ptr)`으로 `p=0x602000`으로 설정되어 DFB가 발생한다.

## Fastbin Duplication
`Fastbin Duplication`은 `fastbin`에서 DFB를 일으키고 동일한 청크를 두 번 할당받도록 하는 공격 기법이다. 이를 이용해 `fastbin`을 조작하여 원하는 주소에 청크를 할당할 수 있다.
```c
// gcc -o fastbin_dup fastbin_dup.c

#include <stdio.h>
#include <stdlib.h>

int main(void){

  char *ptr1 = (char *)malloc(0x40);
  char *ptr2 = (char *)malloc(0x40);
  
  free(ptr1);
  free(ptr2);
  free(ptr1);
  
  fprintf(stderr, "malloc : %p\n", malloc(0x40));
  fprintf(stderr, "malloc : %p\n", malloc(0x40));
  fprintf(stderr, "malloc : %p\n", malloc(0x40));
  
  return 0;
}
```
위 코드는 `Fastbin Duplication`을 이용하여 `ptr1`이 가리키는 청크를 두 번 할당받는 코드다.

### Fastbin Duplication & Poisoning
`Fastbin Poisoning`은 `fastbin`에 있는 청크의 `fd` 값을 조작하여 원하는 주소의 청크로 연결되게 하는 기법이다. 예를 들어 아래와 같이 `fastbin`이 구성됨을 가정하자. 참고로 DFB가 발생한 상황이다.
```c
//bin[0]=A->B->A ...
fastbinsY[0]=A, A->fd=B, B->fd=A, A->fd=B, B->fd=A, ...;
```
이 상태에서 `malloc(0x10)`을 호출하면 `fastbin`이 다음과 같이 변경된다.
```c
//A+0x10 = malloc(0x10)
//bin[0]=B->A ...
fastbinsY[0]=B, B->fd=A, A->fd=B, B->fd=A, ...;
```
이 상태에서 청크 `A`는 ***할당된 청크***이자 ***해제된 청크***이다. 만약 청크 `A`를 할당받는 상태로 값을 쓰면, `A`의 `fd`값이 변경되고, 그 결과 `fastbin`이 조작된다.
```c
//*(long*)(A+0x10) = 0x406030
//bin[0]=B->A->0x406030 ...
fastbinsY[0]=B, B->fd=A, A->fd=0x406030 ...;
```
청크의 구조 `struct malloc_chunk`를 생각하면 쉽게 이해할 수 있다.   
```
 if (__builtin_expect (fastbin_index (chunksize (victim)) != idx, 0))
{
  errstr = "malloc(): memory corruption (fast)";
errout:
  malloc_printerr (check_action, errstr, chunk2mem (victim), av);
  return NULL;
}
```
하지만 유의할 점이 있다. 원하는 주소의 청크를 연결할 때, 해당 청크의 `size`는 연결된 `fastbin`이 보관하는 청크의 크기여야 한다. 위 예시에서 `fastbinsY[0]`는 0x20바이트의 청크를 저장하므로, 0x406030에서 시작하는 청크의 `size`는 0x20이어야 한다.   
위 코드에서 `victim`은 할당하고자 하는 `fastbin` 내의 청크를 의미한다. 해당 청크의 크기가, 그 청크를 보관한 `fastbin`이 저장하는 청크의 크기와 맞는지 검증한다.
