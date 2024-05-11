## Chunk
### Chunk Structure
힙 할당 단위
```C
struct malloc_chunk {

  INTERNAL_SIZE_T      prev_size;  /* Size of previous chunk (if free).  */
  INTERNAL_SIZE_T      size;       /* Size in bytes, including overhead. */

  struct malloc_chunk* fd;         /* double links -- used only if free. */
  struct malloc_chunk* bk;

  /* Only used for large blocks: pointer to next larger size.  */
  struct malloc_chunk* fd_nextsize; /* double links -- used only if free. */
  struct malloc_chunk* bk_nextsize;
};
```
청크는 header(`prev_size`, `size`)와 mem(`fd`부터)으로 나뉜다. 실제 데이터는 mem부터 저장된다. 따라서 `fd`, `bk` 포인터는 청크가 해제(free)되었을 때만 사용된다.
- **prev_size**: 인접한 앞에 있는(낮은 주소) 청크가 free일 경우(`prev_inuse`=0일 경우)의 크기. 병합 목적으로 사용된다.
  > tcache가 도입된 glibc 2.26이상부터는 이 값이 설정되지 않을 수 있으니 [주의](https://c0wb3ll.tistory.com/entry/Heap%EA%B8%B0%EC%B4%88-1)
- **size**: 현재 청크의 크기(header+mem). LSB 3비트는 flag로 사용된다.
  - **PREV_INUSE**(0th bit): 인접한 앞선 청크가 할당된 청크일 경우 1, free일 경우 0. 처음 할당된 청크일 경우 1
  - **IS_MMAPPED**(1st bit): 해당 청크가 `mmap()`으로 할당됐을 때 1
    > Chunks allocated via mmap, which have the second-lowest-order
   bit M (IS_MMAPPED) set in their size fields.  Because they are
   allocated one-by-one, each must contain its own trailing size
   field.  If the M bit is set, the other bits are ignored
   (because mmapped chunks are neither in an arena, nor adjacent
   to a freed chunk).  The M bit is also used for chunks which
   originally came from a dumped heap via malloc_set_state in
   hooks.c. [링크](https://elixir.bootlin.com/glibc/glibc-2.39/source/malloc/malloc.c#L1243)
  - **NON_MAIN_ARENA**(2nd bit): 해당 청크가 `main_arena`에서 관리되지 않을 때 1
- **fd**: 해제된 청크에서만 사용. 동일한 `bin`의 다음 청크를 가리키는 포인터
- **bk**: 해제된 청크에서만 사용. 동일한 `bin`의 이전 청크를 가리키는 포인터
- **fd_nextsize**: `large bin`에서 사용하는 포인터. 현재 청크보다 크기가 작은 청크를 가리키는 포인터
- **bk_nextsize**: `large bin`에서 사용하는 포인터. 현재 청크보다 크기가 큰 청크를 가리키는 포인터

### Type of Chunk
- **Allocate Chunk**: `malloc()`등을 통해 할당된 청크
- **Free Chunk**: `free()`로 해제된 청크
- **Top Chunk(Wildness Chunk)**: 초기에 0x21000만큼의 크기를 가지며, `malloc()` 호출 시 free한 청크가 없다면 해당 청크에서 분리해서 할당

## Bin
해제된 청크가 모여 있는 (단일/이중)연결 리스트. 여러 개의 bin이 존재하며, 각 bin마다 리스트에 포함되는 청크의 크기가 정해져 있다.   
`Fastbin`, `Unsorted bin`, `Smallbin`, `Largebin`이 있다.

- **Fastbin**
  - 0x10(16) ~ 0x40(64) 바이트(32bit)
  - 0x20(32) ~ 0x80(128) 바이트(64bit)
- **Smallbin**
  - < 0x200(512) 바이트(32bit)
  - < 0x400(1024) 바이트(64bit)
- **Largebin**
  - *>*= 0x200(512) 바이트(32bit)
  - *>*= 0x400(1024) 바이트(64bit)

### Fastbin
LIFO, 단일 연결 리스트, bin들 중 할당 해제 속도가 가장 빠르다.   
fastbin[0]:32byte, fastbin[1]:48byte, ..., fastbin[9]:178byte가 존재하지만, 리눅스는 이 중 7개(fastbin[0]:32byte~fastbin[6]:128byte)만을 사용한다. (64bit 기준)  
병합 과정이 없다. 따라서 해제된 청크의 다음 청크의 `prev_inuse`가 0으로 설정되지 않는다.  

### Unsorted bin
FIFO, 이중 연결 리스트, 1개의 bin만 존재한다.   
다음과 같은 조건일 경우 청크가 unsorted bin에 포함된다.
- smallbin, largebin 크기의 청크가 해제됐을 때
  > 해당 크기의 청크는 바로 그 크기에 맞는 bin에 들어가지 않고, 먼저 unsorted bin에 들어간다.
- fastbin에서 청크가 병합됐을 때 
  > fastbin은 기본적으로 병합을 하지 않지만, 큰 크기의 size를 요청받는 등 특정 상황에서는 병합을 수행한다.
  > smallbin, largebin 등에서 청크를 병합하는 함수는 `malloc_consolidate()`이다.
- 요청한 크기의 best fit인 청크의 last remainder
  > 만약 bin에 있는 청크보다 작은 크기를 요청하면, 그 청크를 split하여 제공한다. 이때 분리된 나머지 청크를 `Last Remainder Chunk`라고 한다.

이 bin에 있는 해제된 청크를 재사용하기 위해서는 해당 청크의 크기보다 작거나 같은 크기를 요청해야 한다.   
만약 요청한 크기가 bin에 있는 청크의 크기보다 크다면, 해당 bin 내의 청크들은 각각 smallbin, largebin으로 옮겨진다.   

### Smallbin
FIFO, 이중 연결 리스트이다.   
smallbin[0]:16byte, smallbin[1]:24byte, ..., smallbin[61]:504byte 총 62개의 smallbin이 존재한다.   
해당 bin에서는 병합이 발생한다. 따라서 인접한 다음 청크의 `prev_inuse`가 0으로 설정될 수도 있다. 그러나 이때 병합이 발생해 하나의 청크로 합쳐지므로, 사실상 두 개의 청크가 인접해 있을 수 없다.   

### Largebin
FIFO, 이중 연결 리스트이다.   
glibc 2.23 기준으로 512byte 이상, glibc 2.27 기준 1024byte 이상의 청크가 저장되며, 총 63개의 largebin이 존재한다. 각 largebin은 일정 범위의 크기인 청크를 저장한다.   
> glibc 2.23 기준 largebin[0]: 512<=sz<576, largebin[1]: 576<=sz<640, ...   
> glibc 2.27 기준 largebin[0]:1024<=sz<1088, ..., largebin[32]:3072<=sz<3584, ...

largebin 내의 청크들은 크기 기준으로 내림차순으로 정렬되며 이때 `fd_nextsize`, `bk_nextsize` 포인터를 사용한다. [링크](https://hackstoryadmin.tistory.com/entry/What-is-heap-part-2)   
smallbin과 마찬가지로 병합이 발생한다.   

## Arena
bin(fastbin, unsorted bin, smallbin, largebin)들을 관리하는 객체로, 각 스레드가 접근할 때마다 lock을 건다.   
최대 64개의 arena를 생성할 수 있지만, 스레드의 수가 많을 경우 병목 현상이 생긴다. 따라서 glibc 2.26부터 `tcache`를 도입했다.   
만약 `top chunk`보다 큰 크기를 요청할 경우, `mmap()`으로 할당된 페이지에 청크가 할당되며 이는 `main_arena`에서 관리하지 않는다. 이때 해당 청크의 `NON_MAIN_ARENA` 값이 1이 된다.
```C
static struct malloc_state main_arena =
{
  .mutex = _LIBC_LOCK_INITIALIZER,
  .next = &main_arena,
  .attached_threads = 1
};

struct malloc_state
{
  /* Serialize access.  */
  mutex_t mutex;

  /* Flags (formerly in max_fast).  */
  int flags;

  /* Fastbins */
  mfastbinptr fastbinsY[NFASTBINS];

  /* Base of the topmost chunk -- not otherwise kept in a bin */
  mchunkptr top;

  /* The remainder from the most recent split of a small request */
  mchunkptr last_remainder;

  /* Normal bins packed as described above */
  mchunkptr bins[NBINS * 2 - 2];

  /* Bitmap of bins */
  unsigned int binmap[BINMAPSIZE];

  /* Linked list */
  struct malloc_state *next;

  /* Linked list for free arenas.  Access to this field is serialized
     by free_list_lock in arena.c.  */
  struct malloc_state *next_free;

  /* Number of threads attached to this arena.  0 if the arena is on
     the free list.  Access to this field is serialized by
     free_list_lock in arena.c.  */
  INTERNAL_SIZE_T attached_threads;

  /* Memory allocated from the system in this arena.  */
  INTERNAL_SIZE_T system_mem;
  INTERNAL_SIZE_T max_system_mem;
};
```

## Reference
[Background: ptmalloc2, Dreamhack](https://dreamhack.io/lecture/courses/569)   
[Heap Allocator Exploit, Dreamhack](https://dreamhack.io/lecture/courses/16)   
[Binary Exploitation-Heap, ir0nstone](https://ir0nstone.gitbook.io/notes/types/heap)   
[What is heap - part 1, fkillrra's note](https://hackstoryadmin.tistory.com/entry/What-is-heap-part1)   
[What is heap - part 2, fkillrra's note](https://hackstoryadmin.tistory.com/entry/What-is-heap-part-2)   
[Heap Basics - Bin, 노션으로 옮김](https://velog.io/@woounnan/SYSTEM-Heap-Basics-Bin) 
